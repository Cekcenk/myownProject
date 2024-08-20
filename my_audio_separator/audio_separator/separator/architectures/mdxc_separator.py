import os
import sys

import torch
import numpy as np
from tqdm import tqdm
from ml_collections import ConfigDict
from scipy import signal
from torch.cuda.amp import autocast
from torch.utils.data import DataLoader, TensorDataset
import torchaudio
from apex import amp
import torch.nn.functional as F

# Enable CUDA optimizations
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.enabled = True
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

from audio_separator.separator.common_separator import CommonSeparator
from audio_separator.separator.uvr_lib_v5 import spec_utils
from audio_separator.separator.uvr_lib_v5.tfc_tdf_v3 import TFC_TDF_net
from audio_separator.separator.uvr_lib_v5.mel_band_roformer import MelBandRoformer
from audio_separator.separator.uvr_lib_v5.bs_roformer import BSRoformer


class MDXCSeparator(CommonSeparator):
    """
    MDXCSeparator is responsible for separating audio sources using MDXC models.
    It initializes with configuration parameters and prepares the model for separation tasks.
    """

    def __init__(self, common_config, arch_config):
        # Any configuration values which can be shared between architectures should be set already in CommonSeparator,
        # e.g. user-specified functionality choices (self.output_single_stem) or common model parameters (self.primary_stem_name)
        super().__init__(config=common_config)

        # Model data is basic overview metadata about the model, e.g. which stem is primary and whether it's a karaoke model
        # It's loaded in from model_data_new.json in Separator.load_model and there are JSON examples in that method
        # The instance variable self.model_data is passed through from Separator and set in CommonSeparator
        self.logger.debug(f"Model data: {self.model_data}")

        # Arch Config is the MDXC architecture specific user configuration options, which should all be configurable by the user
        # either by their Separator class instantiation or by passing in a CLI parameter.
        # While there are similarities between architectures for some of these (e.g. batch_size), they are deliberately configured
        # this way as they have architecture-specific default values.
        self.segment_size = arch_config.get("segment_size", 512)  # Increased from 256
        self.override_model_segment_size = arch_config.get("override_model_segment_size", False)
        self.overlap = arch_config.get("overlap", 4)  # Reduced from 8
        self.batch_size = arch_config.get("batch_size", 64)  # Increased batch size
        self.pitch_shift = arch_config.get("pitch_shift", 2)

        self.logger.debug(f"MDXC arch params: batch_size={self.batch_size}, segment_size={self.segment_size}, overlap={self.overlap}")
        self.logger.debug(f"MDXC arch params: override_model_segment_size={self.override_model_segment_size}, pitch_shift={self.pitch_shift}")

        self.is_roformer = "is_roformer" in self.model_data

        self.load_model()

        self.primary_source = None
        self.secondary_source = None
        self.audio_file_path = None
        self.audio_file_base = None

        self.is_vocal_main_target = True if self.model_data_cfgdict.training.target_instrument == "Vocals" else False
        self.logger.debug(f"is_vocal_main_target: {self.is_vocal_main_target}")

        self.scaler = torch.cuda.amp.GradScaler()

        # Apply JIT compilation
        self.model_run = torch.jit.script(self.model_run)

        # Initialize Apex for mixed precision
        self.model_run, self.optimizer = amp.initialize(self.model_run, self.optimizer, opt_level="O1")

        # Use DataParallel if multiple GPUs are available
        if torch.cuda.device_count() > 1:
            self.model_run = torch.nn.DataParallel(self.model_run)

        self.logger.info("MDXC Separator initialisation complete")

    def load_model(self):
        """
        Load the model into memory from file on disk, initialize it with config from the model data,
        and prepare for inferencing using hardware accelerated Torch device.
        """
        self.logger.debug("Loading checkpoint model for inference...")

        self.model_data_cfgdict = ConfigDict(self.model_data)

        try:
            if self.is_roformer:
                self.logger.debug("Loading Roformer model...")

                # Determine the model type based on the configuration and instantiate it
                if "num_bands" in self.model_data_cfgdict.model:
                    self.logger.debug("Loading MelBandRoformer model...")
                    model = MelBandRoformer(**self.model_data_cfgdict.model)
                elif "freqs_per_bands" in self.model_data_cfgdict.model:
                    self.logger.debug("Loading BSRoformer model...")
                    model = BSRoformer(**self.model_data_cfgdict.model)
                else:
                    raise ValueError("Unknown Roformer model type in the configuration.")

                # Load model checkpoint
                checkpoint = torch.load(self.model_path, map_location="cpu")
                self.model_run = model if not isinstance(model, torch.nn.DataParallel) else model.module
                self.model_run.load_state_dict(checkpoint)
                self.model_run.to(self.torch_device).eval()

            else:
                self.logger.debug("Loading TFC_TDF_net model...")
                self.model_run = TFC_TDF_net(self.model_data_cfgdict, device=self.torch_device)
                self.model_run.load_state_dict(torch.load(self.model_path, map_location=self.torch_device))
                self.model_run.to(self.torch_device).eval()

        except RuntimeError as e:
            self.logger.error(f"Error: {e}")
            self.logger.error("An error occurred while loading the model file. This often occurs when the model file is corrupt or incomplete.")
            self.logger.error(f"Please try deleting the model file from {self.model_path} and run audio-separator again to re-download it.")
            sys.exit(1)

    def separate(self, audio_file_path):
        """
        Separates the audio file into primary and secondary sources based on the model's configuration.
        It processes the mix, demixes it into sources, normalizes the sources, and saves the output files.

        Args:
            audio_file_path (str): The path to the audio file to be processed.

        Returns:
            list: A list of paths to the output files generated by the separation process.
        """
        self.primary_source = None
        self.secondary_source = None

        self.audio_file_path = audio_file_path
        self.audio_file_base = os.path.splitext(os.path.basename(audio_file_path))[0]

        self.logger.debug(f"Preparing mix for input audio file {self.audio_file_path}...")
        mix = self.prepare_mix(self.audio_file_path)

        self.logger.debug("Normalizing mix before demixing...")
        mix = spec_utils.normalize(wave=mix, max_peak=self.normalization_threshold)

        source = self.demix(mix=mix)
        self.logger.debug("Demixing completed.")

        output_files = []
        self.logger.debug("Processing output files...")

        if not isinstance(self.primary_source, np.ndarray):
            self.logger.debug(f"Normalizing primary source for primary stem {self.primary_stem_name}...")
            self.primary_source = spec_utils.normalize(wave=source[self.primary_stem_name], max_peak=self.normalization_threshold).T

        if not isinstance(self.secondary_source, np.ndarray):
            self.logger.debug(f"Normalizing secondary source for secondary stem {self.secondary_stem_name}...")
            self.secondary_source = spec_utils.normalize(wave=source[self.secondary_stem_name], max_peak=self.normalization_threshold).T

        if not self.output_single_stem or self.output_single_stem.lower() == self.secondary_stem_name.lower():
            self.secondary_stem_output_path = os.path.join(f"{self.audio_file_base}_({self.secondary_stem_name})_{self.model_name}.{self.output_format.lower()}")

            self.logger.info(f"Saving {self.secondary_stem_name} stem to {self.secondary_stem_output_path}...")
            self.final_process(self.secondary_stem_output_path, self.secondary_stem_output_path, self.secondary_stem_name)
            output_files.append(self.secondary_stem_output_path)

        if not self.output_single_stem or self.output_single_stem.lower() == self.primary_stem_name.lower():
            self.primary_stem_output_path = os.path.join(f"{self.audio_file_base}_({self.primary_stem_name})_{self.model_name}.{self.output_format.lower()}")

            if not isinstance(self.primary_source, np.ndarray):
                self.primary_source = source.T

            self.logger.info(f"Saving {self.primary_stem_name} stem to {self.primary_stem_output_path}...")
            self.final_process(self.primary_stem_output_path, self.primary_source, self.primary_stem_name)
            output_files.append(self.primary_stem_output_path)
        return output_files

    def pitch_fix(self, source, sr_pitched, orig_mix):
        """
        Change the pitch of the source audio by a number of semitones.

        Args:
            source (np.ndarray): The source audio to be pitch-shifted.
            sr_pitched (int): The sample rate of the pitch-shifted audio.
            orig_mix (np.ndarray): The original mix, used to match the shape of the pitch-shifted audio.

        Returns:
            np.ndarray: The pitch-shifted source audio.
        """
        source = spec_utils.change_pitch_semitones(source, sr_pitched, semitone_shift=self.pitch_shift)[0]
        source = spec_utils.match_array_shapes(source, orig_mix)
        return source

    def overlap_add(self, result, x, weights, start, length):
        """
        Adds the overlapping part of the result to the result tensor.
        """
        x = x.to(result.device)
        weights = weights.to(result.device)
        result[..., start : start + length] += x[..., :length] * weights[:length]
        return result

    def demix(self, mix: torch.Tensor) -> dict:
        orig_mix = mix.cpu().numpy()

        if self.pitch_shift != 0:
            self.logger.debug(f"Shifting pitch by -{self.pitch_shift} semitones...")
            mix = torchaudio.functional.pitch_shift(mix, self.sample_rate, -self.pitch_shift)

        mix = mix.to(self.torch_device)

        try:
            num_stems = self.model_run.num_target_instruments
        except AttributeError:
            num_stems = self.model_run.module.num_target_instruments
        self.logger.debug(f"Number of stems: {num_stems}")

        if self.override_model_segment_size:
            mdx_segment_size = self.segment_size
        else:
            mdx_segment_size = self.model_data_cfgdict.inference.dim_t
        self.logger.debug(f"Using segment size: {mdx_segment_size}")

        chunk_size = self.model_data_cfgdict.audio.hop_length * (mdx_segment_size - 1)
        hop_size = chunk_size // self.overlap

        mix_shape = mix.shape[1]
        pad_size = hop_size - (mix_shape - chunk_size) % hop_size

        mix = F.pad(mix, (0, pad_size + chunk_size - hop_size))

        chunks = mix.unfold(1, chunk_size, hop_size).transpose(0, 1)

        # Use DataLoader for efficient data loading
        dataset = TensorDataset(chunks)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, num_workers=8, pin_memory=True)  # Increased num_workers

        accumulated_outputs = torch.zeros(num_stems, *mix.shape, device=self.torch_device)

        with torch.no_grad(), autocast():
            for batch in tqdm(dataloader):
                batch_result = self.model_run(batch[0].to(self.torch_device))
                for i, result in enumerate(batch_result):
                    start = i * hop_size
                    accumulated_outputs[..., start:start + chunk_size] += result

        inferenced_outputs = accumulated_outputs[..., :mix_shape] / self.overlap
        del accumulated_outputs

        if num_stems > 1 or self.is_vocal_main_target:
            sources = {}
            for key, value in zip(self.model_data_cfgdict.training.instruments, inferenced_outputs.cpu().numpy()):
                if self.pitch_shift != 0:
                    sources[key] = self.pitch_fix(value, self.sample_rate, orig_mix)
                else:
                    sources[key] = value

            if self.is_vocal_main_target:
                if sources["Vocals"].shape[1] != orig_mix.shape[1]:
                    sources["Vocals"] = np.pad(sources["Vocals"], ((0, 0), (0, orig_mix.shape[1] - sources["Vocals"].shape[1])))
                sources["Instrumental"] = orig_mix - sources["Vocals"]

            return sources
        else:
            inferenced_output = inferenced_outputs[0].cpu().numpy()
            if self.pitch_shift != 0:
                return self.pitch_fix(inferenced_output, self.sample_rate, orig_mix)
            else:
                return inferenced_output

    def profile_demix(self, mix):
        with torch.profiler.profile(
            activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA],
            record_shapes=True,
            profile_memory=True,
            with_stack=True
        ) as prof:
            self.demix(mix)
        print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=10))

    def prepare_mix(self, mix):
        if isinstance(mix, str):
            waveform, sample_rate = torchaudio.load(mix)
            waveform = waveform.to(self.torch_device, non_blocking=True)  # Use non_blocking for faster transfer
        else:
            waveform = torch.tensor(mix, device=self.torch_device, non_blocking=True)
        
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0).repeat(2, 1)
        
        return waveform
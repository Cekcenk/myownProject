import os
import sys
import fairseq
import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"

def printt(strr):
    print(strr)
    # You might want to log this to a file as well

def get_device(device):
    if "privateuseone" not in device:
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    else:
        import torch_directml
        return torch_directml.device(torch_directml.default_device())

def load_hubert(device, is_half):
    models, _, _ = fairseq.checkpoint_utils.load_model_ensemble_and_task(
        ["hubert_base.pt"],
        suffix="",
    )
    hubert_model = models[0]
    hubert_model = hubert_model.to(device)
    if is_half:
        hubert_model = hubert_model.half()
    else:
        hubert_model = hubert_model.float()
    hubert_model.eval()
    return hubert_model

def extract_features(device, n_part, i_part, i_gpu, exp_dir, version, is_half):
    device = get_device(device)
    if device == "cuda":
        os.environ["CUDA_VISIBLE_DEVICES"] = str(i_gpu)
    
    printt(f"Device: {device}")
    printt(f"Extracting features for part {i_part + 1}/{n_part}")

    # Load the HuBERT model
    hubert_model = load_hubert(device, is_half)

    # Set up input and output directories
    inp_root = f"{exp_dir}/1_16k_wavs"
    opt_root = f"{exp_dir}/3_feature256" if version == "v1" else f"{exp_dir}/3_feature768"
    os.makedirs(opt_root, exist_ok=True)

    # Get the list of files to process
    names = sorted(list(os.listdir(inp_root)))
    for name in names[i_part::n_part]:
        inp_path = f"{inp_root}/{name}"
        opt_path = f"{opt_root}/{name}"

        if os.path.exists(opt_path):
            printt(f"Skipping {name} as it already exists")
            continue

        printt(f"Extracting features for {name}")
        
        # Load and preprocess the audio
        wav, sr = sf.read(inp_path)
        wav = torch.from_numpy(wav).to(device)
        if len(wav.shape) == 2:
            wav = wav.mean(-1)
        wav = F.pad(wav, ((400 - 320) // 2, (400 - 320) // 2))
        wav = wav.unsqueeze(0)

        # Extract features
        with torch.no_grad():
            feat = hubert_model.extract_features(wav, padding_mask=None, mask=False)[0]
        feat = feat.squeeze(0).float().cpu().numpy()

        # Save the extracted features
        np.save(opt_path, feat, allow_pickle=False)

    printt(f"Feature extraction completed for part {i_part + 1}/{n_part}")
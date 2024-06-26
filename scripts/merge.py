from pydub import AudioSegment

def overlay_audio_files(file1, file2, output_file):
    # Load the two audio files
    audio1 = AudioSegment.from_file(file1)
    audio2 = AudioSegment.from_file(file2)

    # Overlay audio2 on top of audio1
    overlaid_audio = audio1.overlay(audio2)

    # Export the overlaid audio file
    overlaid_audio.export(output_file, format="mp3")

    print(f"Overlaid audio file saved as {output_file}")

# Example usage
# overlay_audio_files('vocal.wav', 'instrumental.wav', 'merged_audio.mp3')

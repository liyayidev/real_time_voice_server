import wave
import sys
import os

def raw_pcm_to_wav(pcm_file, wav_file, channels=1, rate=16000, width=2):
    """
    Converts raw PCM (signed 16-bit little endian) to WAV.
    """
    if not os.path.exists(pcm_file):
        print(f"File not found: {pcm_file}")
        return

    with open(pcm_file, 'rb') as pcm:
        pcm_data = pcm.read()
        
    with wave.open(wav_file, 'wb') as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(pcm_data)
    
    print(f"Converted {pcm_file} -> {wav_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python decode_recording.py <input.pcm> [output.wav]")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file + ".wav"
    
    raw_pcm_to_wav(input_file, output_file)

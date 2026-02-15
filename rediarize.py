"""
Auto-Detecting Speaker Diarization Script.
Uses Silhouette Score to automatically find the optimal number of speakers.
"""
import sys
import os
import re
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from pydub import AudioSegment
import soundfile as sf
import tempfile

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0: return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def parse_time(t):
    parts = t.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return int(parts[0]) * 60 + int(parts[1])

def parse_existing_transcript(filepath):
    segments = []
    if not os.path.exists(filepath): return []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("---"): continue
            match = re.match(r'\s*\[(\d+:\d+(?::\d+)?) - (\d+:\d+(?::\d+)?)\]\s*(.*)', line)
            if match:
                start_str, end_str, text = match.groups()
                segments.append({"start": parse_time(start_str), "end": parse_time(end_str), "text": text})
    return segments

def load_audio_as_wav(audio_path):
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio.export(tmp.name, format="wav")
        wav_data, sr = sf.read(tmp.name)
        os.unlink(tmp.name)
    return wav_data.astype(np.float32)

def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "audio.m4a"
    transcript_path = "transcript.txt"

    print("[1/3] Parsing existing transcript...")
    segments = parse_existing_transcript(transcript_path)
    if not segments:
        print("ERROR: transcript.txt not found or empty.")
        sys.exit(1)

    print("[2/3] Extracting voice embeddings (High Resolution)...")
    wav = load_audio_as_wav(audio_path)
    encoder = VoiceEncoder("cpu")
    
    # 1.5s windows with 0.75s hop for high precision
    embeddings = []
    time_points = []
    total_duration = len(wav) / 16000
    
    for start_t in np.arange(0, total_duration - 1.5, 0.75):
        s = int(start_t * 16000)
        e = int((start_t + 1.5) * 16000)
        chunk = wav[s:e]
        if np.abs(chunk).mean() < 0.005: continue # Skip silence
        try:
            embeddings.append(encoder.embed_utterance(chunk))
            time_points.append(start_t + 0.75)
        except: pass

    embeddings = np.array(embeddings)
    
    print("[3/3] Auto-detecting optimal number of speakers...")
    best_n = 2
    max_score = -1
    best_labels = None
    
    # Test from 2 to 8 speakers to find the "sweet spot"
    for n in range(2, 9):
        clustering = AgglomerativeClustering(n_clusters=n, metric='cosine', linkage='average')
        labels = clustering.fit_predict(embeddings)
        score = silhouette_score(embeddings, labels, metric='cosine')
        print(f"  Testing {n} speakers... Score: {score:.4f}")
        if score > max_score:
            max_score = score
            best_n = n
            best_labels = labels

    print(f"\n✨ Optimal speaker count detected: {best_n}")

    # Map labels back to segments
    output_lines = []
    prev_speaker = None
    for seg in segments:
        mid = (seg["start"] + seg["end"]) / 2
        idx = np.abs(np.array(time_points) - mid).argmin()
        speaker_name = f"Speaker {best_labels[idx] + 1}"
        ts = f"[{format_time(seg['start'])} - {format_time(seg['end'])}]"
        if speaker_name != prev_speaker:
            output_lines.append(f"\n--- {speaker_name} ---")
            prev_speaker = speaker_name
        output_lines.append(f"  {ts} {seg['text']}")

    with open("transcript_speakers.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines).strip())
    
    print(f"📄 Saved to: transcript_speakers.txt")

if __name__ == "__main__":
    main()

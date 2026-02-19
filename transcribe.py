import sys
import json
import os
import platform
import numpy as np
from faster_whisper import WhisperModel
from resemblyzer import VoiceEncoder, preprocess_wav
from sklearn.cluster import AgglomerativeClustering
from pydub import AudioSegment
import tempfile
import soundfile as sf
import torch


def get_device():
    """Auto-detect the best available device for inference.

    Note: faster-whisper doesn't support MPS (Apple Silicon) yet, so we use CPU.
    For GPU acceleration on Apple Silicon, consider using the original Whisper model.
    """
    if torch.cuda.is_available():
        return "cuda", "float16"  # NVIDIA GPU
    else:
        return "cpu", "int8"  # CPU (MPS not supported by faster-whisper yet)


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def load_audio_as_wav(audio_path):
    """Load any audio file and convert to 16kHz mono WAV numpy array."""
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio.export(tmp.name, format="wav")
        wav_data, sr = sf.read(tmp.name)
        os.unlink(tmp.name)

    return wav_data.astype(np.float32)


def transcribe_with_speakers(audio_path, model_size="large-v3-turbo", num_speakers=None):
    # Step 1: Auto-detect device
    device, compute_type = get_device()
    print(f"[Device Detection]")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Using device: {device.upper()}")
    print(f"  Compute type: {compute_type}")
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        print(f"  GPU: {gpu_name}")

    # Step 2: Transcribe with timestamps
    print(f"\n[1/4] Loading Whisper model: {model_size}")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    print(f"[2/4] Transcribing: {audio_path}")
    print(f"  Language: Indonesian (enforced)")
    print(f"  Beam size: 5 (optimized for accuracy)")

    # Enhanced transcription parameters
    raw_segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language="id",
        vad_filter=True,  # Enable VAD to skip silence
        vad_parameters={
            "min_speech_duration_ms": 500,
            "min_silence_duration_ms": 1000,
            "speech_pad_ms": 400
        },
        word_timestamps=True  # Get word-level timestamps for better diarization
    )
    print(f"  Detected language: '{info.language}' (prob: {info.language_probability:.2f})")

    # Collect all segments
    segments = []
    for seg in raw_segments:
        segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip()
        })
    print(f"  Total segments: {len(segments)}")

    # Step 3: Load audio for speaker embeddings
    print(f"[3/4] Loading audio & computing speaker embeddings...")
    wav = load_audio_as_wav(audio_path)

    # Use GPU for encoder if available (MPS not supported by resemblyzer)
    encoder_device = device if device == "cuda" else "cpu"
    print(f"  Encoder device: {encoder_device.upper()}")
    encoder = VoiceEncoder(encoder_device)

    # Group small segments into chunks (~10s) for better embeddings
    chunks = []
    current_chunk_segments = []
    current_duration = 0

    for seg in segments:
        duration = seg["end"] - seg["start"]
        current_chunk_segments.append(seg)
        current_duration += duration

        if current_duration >= 8.0:
            chunk_start = current_chunk_segments[0]["start"]
            chunk_end = current_chunk_segments[-1]["end"]
            chunks.append({
                "start": chunk_start,
                "end": chunk_end,
                "segments": list(current_chunk_segments)
            })
            current_chunk_segments = []
            current_duration = 0

    # Don't forget remaining segments
    if current_chunk_segments:
        chunks.append({
            "start": current_chunk_segments[0]["start"],
            "end": current_chunk_segments[-1]["end"],
            "segments": list(current_chunk_segments)
        })

    print(f"  Grouped into {len(chunks)} chunks for embedding")

    # Get speaker embeddings for each chunk
    embeddings = []
    valid_chunks = []
    for i, chunk in enumerate(chunks):
        start_sample = int(chunk["start"] * 16000)
        end_sample = int(chunk["end"] * 16000)
        segment_wav = wav[start_sample:min(end_sample, len(wav))]

        if len(segment_wav) < 1600:  # Skip chunks < 0.1s
            continue

        try:
            embedding = encoder.embed_utterance(segment_wav)
            embeddings.append(embedding)
            valid_chunks.append(chunk)
        except Exception as e:
            print(f"  Warning: skipped chunk {i} ({e})")

    print(f"  Computed {len(embeddings)} embeddings")

    # Step 3: Cluster speakers
    print(f"[4/4] Clustering speakers...")
    embeddings_array = np.array(embeddings)

    if num_speakers and num_speakers > 1:
        # When num_speakers is specified, use it directly
        clustering = AgglomerativeClustering(n_clusters=num_speakers)
        labels = clustering.fit_predict(embeddings_array)
    else:
        # Try progressively lower thresholds until we get >1 speaker
        best_labels = None
        for threshold in [0.55, 0.45, 0.35, 0.25]:
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=threshold,
                metric="cosine",
                linkage="average"
            )
            labels = clustering.fit_predict(embeddings_array)
            n = len(set(labels))
            print(f"  Threshold {threshold}: {n} speakers")
            if 2 <= n <= 15:
                best_labels = labels
                break
            best_labels = labels

        labels = best_labels
    n_speakers = len(set(labels))
    print(f"  Detected {n_speakers} speakers")

    # Step 4: Build output with speaker labels
    output_lines = []
    prev_speaker = None

    for chunk, label in zip(valid_chunks, labels):
        speaker = f"Speaker {label + 1}"

        for seg in chunk["segments"]:
            timestamp = f"[{format_time(seg['start'])} - {format_time(seg['end'])}]"

            if speaker != prev_speaker:
                output_lines.append("")
                output_lines.append(f"--- {speaker} ---")
                prev_speaker = speaker

            output_lines.append(f"  {timestamp} {seg['text']}")

    return "\n".join(output_lines).strip(), n_speakers


if __name__ == "__main__":
    import time

    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file> [num_speakers] [output_basename]")
        print("\nExamples:")
        print("  python transcribe.py meeting.m4a")
        print("  python transcribe.py meeting.m4a 5  # Specify 5 speakers")
        print("  python transcribe.py meeting.m4a 5 meeting  # Output to meeting_speakers.txt")
        print("  python transcribe.py meeting.m4a meeting  # Auto-detect speakers, output to meeting_speakers.txt")
        sys.exit(1)

    file_path = sys.argv[1]

    # Parse arguments: can be either:
    # - transcribe.py audio.m4a num_speakers output_base
    # - transcribe.py audio.m4a output_base (when 2nd arg is not a number)
    num_speakers = None
    output_base = "transcript"

    if len(sys.argv) >= 3:
        # Check if 2nd arg is a number
        try:
            num_speakers = int(sys.argv[2])
            if len(sys.argv) >= 4:
                output_base = sys.argv[3]
        except ValueError:
            # 2nd arg is not a number, so it's the output_base
            output_base = sys.argv[2]

    if not os.path.exists(file_path):
        print(json.dumps({"error": f"File not found: {file_path}"}))
        sys.exit(1)

    try:
        start_time = time.time()
        result, n_speakers = transcribe_with_speakers(file_path, num_speakers=num_speakers)
        elapsed_time = time.time() - start_time

        output_file = f"{output_base}_speakers.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)

        print(f"\n{'='*60}")
        print(f"✅ TRANSCRIPTION COMPLETE!")
        print(f"{'='*60}")
        print(f"📄 Output file: {output_file}")
        print(f"👥 Speakers detected: {n_speakers}")
        print(f"⏱️  Processing time: {elapsed_time:.2f} seconds")
        print(f"{'='*60}")
        print(f"\n--- Preview (first 500 chars) ---")
        print(result[:500])
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

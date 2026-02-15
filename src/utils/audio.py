"""
Audio processing utilities for transcription system.
"""
import numpy as np
import tempfile
import os
from pathlib import Path
from typing import Tuple, Optional
from pydub import AudioSegment
import soundfile as sf


def load_audio_as_wav(audio_path: str, sample_rate: int = 16000) -> np.ndarray:
    """
    Load any audio file and convert to mono WAV numpy array.

    Args:
        audio_path: Path to audio file (mp3, m4a, wav, etc.)
        sample_rate: Target sample rate (default 16000 for Whisper)

    Returns:
        Audio data as float32 numpy array
    """
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_frame_rate(sample_rate).set_channels(1).set_sample_width(2)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio.export(tmp.name, format="wav")
        wav_data, sr = sf.read(tmp.name)
        os.unlink(tmp.name)

    return wav_data.astype(np.float32)


def get_audio_duration(audio_path: str) -> float:
    """
    Get audio file duration in seconds.

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds
    """
    audio = AudioSegment.from_file(audio_path)
    return len(audio) / 1000.0


def detect_silence(
    audio: np.ndarray,
    sample_rate: int = 16000,
    threshold: float = 0.01,
    min_duration: float = 0.5
) -> list:
    """
    Detect silent segments in audio.

    Args:
        audio: Audio data as numpy array
        sample_rate: Sample rate
        threshold: Amplitude threshold for silence
        min_duration: Minimum silence duration in seconds

    Returns:
        List of (start, end) tuples for silent segments
    """
    # Calculate amplitude envelope
    amplitude = np.abs(audio)
    is_silent = amplitude < threshold

    silent_segments = []
    start = None

    for i, silent in enumerate(is_silent):
        if silent and start is None:
            start = i / sample_rate
        elif not silent and start is not None:
            end = i / sample_rate
            if end - start >= min_duration:
                silent_segments.append((start, end))
            start = None

    return silent_segments


def remove_silence(
    audio_path: str,
    output_path: Optional[str] = None,
    threshold: float = 0.01,
    min_silence_duration: float = 0.5
) -> str:
    """
    Remove silence from audio file.

    Args:
        audio_path: Input audio path
        output_path: Output path (if None, generates temp file)
        threshold: Amplitude threshold
        min_silence_duration: Minimum silence to remove

    Returns:
        Path to processed audio file
    """
    audio = AudioSegment.from_file(audio_path)

    # Split audio on silence
    chunks = audio.split_on_silence(
        min_silence_len=int(min_silence_duration * 1000),
        silence_thresh=int(threshold * 1000),
        keep_silence=100  # Keep 100ms of silence
    )

    # Combine non-silent chunks
    output_audio = chunks[0]
    for chunk in chunks[1:]:
        output_audio += chunk

    if output_path is None:
        output_path = tempfile.mktemp(suffix=".wav")

    output_audio.export(output_path, format="wav")
    return output_path


def segment_audio(
    audio_path: str,
    segment_duration: float = 30.0,
    overlap: float = 5.0
) -> list:
    """
    Segment audio into overlapping chunks.

    Args:
        audio_path: Input audio path
        segment_duration: Duration of each segment in seconds
        overlap: Overlap between segments in seconds

    Returns:
        List of (start, end, temp_path) tuples
    """
    audio = AudioSegment.from_file(audio_path)
    duration = len(audio) / 1000.0

    segments = []
    start = 0.0

    while start < duration:
        end = min(start + segment_duration, duration)

        # Extract segment
        segment = audio[int(start * 1000):int(end * 1000)]

        # Save to temp file
        temp_path = tempfile.mktemp(suffix=".wav")
        segment.export(temp_path, format="wav")

        segments.append((start, end, temp_path))

        start = end - overlap

        # Break if we've covered the whole audio
        if end >= duration:
            break

    return segments


def normalize_audio(audio_path: str, output_path: Optional[str] = None) -> str:
    """
    Normalize audio volume.

    Args:
        audio_path: Input audio path
        output_path: Output path (if None, generates temp file)

    Returns:
        Path to normalized audio file
    """
    audio = AudioSegment.from_file(audio_path)

    # Normalize to -20 dBFS
    normalized = audio.normalize(headroom=20.0)

    if output_path is None:
        output_path = tempfile.mktemp(suffix=".wav")

    normalized.export(output_path, format="wav")
    return output_path


def convert_to_mono(audio_path: str, output_path: Optional[str] = None) -> str:
    """
    Convert stereo audio to mono.

    Args:
        audio_path: Input audio path
        output_path: Output path (if None, generates temp file)

    Returns:
        Path to mono audio file
    """
    audio = AudioSegment.from_file(audio_path)
    mono = audio.set_channels(1)

    if output_path is None:
        output_path = tempfile.mktemp(suffix=".wav")

    mono.export(output_path, format="wav")
    return output_path


def resample_audio(
    audio_path: str,
    target_sample_rate: int = 16000,
    output_path: Optional[str] = None
) -> str:
    """
    Resample audio to target sample rate.

    Args:
        audio_path: Input audio path
        target_sample_rate: Target sample rate
        output_path: Output path (if None, generates temp file)

    Returns:
        Path to resampled audio file
    """
    audio = AudioSegment.from_file(audio_path)
    resampled = audio.set_frame_rate(target_sample_rate)

    if output_path is None:
        output_path = tempfile.mktemp(suffix=".wav")

    resampled.export(output_path, format="wav")
    return output_path


def preprocess_audio(
    audio_path: str,
    output_path: Optional[str] = None,
    normalize: bool = True,
    to_mono: bool = True,
    sample_rate: int = 16000
) -> str:
    """
    Apply all preprocessing steps to audio.

    Args:
        audio_path: Input audio path
        output_path: Output path (if None, generates temp file)
        normalize: Whether to normalize volume
        to_mono: Whether to convert to mono
        sample_rate: Target sample rate

    Returns:
        Path to preprocessed audio file
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".wav")

    audio = AudioSegment.from_file(audio_path)

    if to_mono:
        audio = audio.set_channels(1)

    audio = audio.set_frame_rate(sample_rate)

    if normalize:
        audio = audio.normalize(headroom=20.0)

    audio.export(output_path, format="wav")
    return output_path

"""
Enhanced transcription module using faster-whisper with GPU support.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import time

import torch
from faster_whisper import WhisperModel

from .utils.config import get_config
from .utils.audio import load_audio_as_wav, get_audio_duration


logger = logging.getLogger(__name__)


class EnhancedTranscriber:
    """
    High-accuracy Indonesian speech transcriber using Whisper.

    Features:
    - Support for large-v3-turbo model (best accuracy/speed balance)
    - GPU acceleration (CUDA, MPS, CPU fallback)
    - VAD (Voice Activity Detection) to skip silence
    - Word-level timestamps for better diarization
    - Indonesian language enforcement
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize transcriber with configuration.

        Args:
            config_path: Optional path to config file
        """
        self.config = get_config(config_path)
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load Whisper model with optimal settings."""
        model_size = self.config.get('transcription', 'model')
        device = self.config.get('transcription', 'device')
        compute_type = self.config.get('transcription', 'compute_type')

        logger.info(f"Loading Whisper model: {model_size}")
        logger.info(f"Device: {device.upper()}, Compute type: {compute_type}")

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

        # Log device info
        if device == 'cuda':
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU: {gpu_name}")
        elif device == 'mps':
            logger.info("Apple Silicon GPU acceleration enabled")

    def transcribe(
        self,
        audio_path: str,
        language: str = "id",
        beam_size: Optional[int] = None,
        vad_filter: Optional[bool] = None,
        word_timestamps: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Transcribe audio file with timestamps.

        Args:
            audio_path: Path to audio file
            language: Language code (default: 'id' for Indonesian)
            beam_size: Beam size for decoding (default from config)
            vad_filter: Enable VAD to skip silence (default from config)
            word_timestamps: Include word-level timestamps
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (segments, info) where:
                - segments: List of segment dicts with start, end, text
                - info: Dict with metadata (language, duration, etc.)
        """
        if not self.model:
            self._load_model()

        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Get parameters from config if not specified
        if beam_size is None:
            beam_size = self.config.get('transcription', 'beam_size')
        if vad_filter is None:
            vad_filter = self.config.get('transcription', 'vad', 'enabled')

        # Get audio duration
        duration = get_audio_duration(audio_path)

        logger.info(f"Transcribing: {audio_path}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Language: {language} (enforced)")
        logger.info(f"VAD: {('enabled' if vad_filter else 'disabled')}")
        logger.info(f"Beam size: {beam_size}")

        start_time = time.time()

        # Prepare VAD parameters
        vad_params = None
        if vad_filter:
            vad_params = {
                "min_speech_duration_ms": self.config.get('transcription', 'vad', 'min_speech_duration_ms'),
                "min_silence_duration_ms": self.config.get('transcription', 'vad', 'min_silence_duration_ms'),
                "speech_pad_ms": self.config.get('transcription', 'vad', 'speech_pad_ms'),
            }

        # Transcribe
        segments_gen, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            vad_parameters=vad_params,
            word_timestamps=word_timestamps
        )

        # Collect segments
        segments = []
        for seg in segments_gen:
            segment_data = {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            }

            # Add word timestamps if available
            if word_timestamps and hasattr(seg, 'words'):
                segment_data["words"] = [
                    {
                        "start": w.start,
                        "end": w.end,
                        "word": w.word,
                        "probability": w.probability
                    }
                    for w in seg.words
                ]

            segments.append(segment_data)

            if progress_callback:
                progress = min(seg.end / duration * 100, 100)
                progress_callback(progress)

        elapsed = time.time() - start_time
        real_time_factor = elapsed / duration if duration > 0 else 0

        logger.info(f"Transcription complete: {len(segments)} segments")
        logger.info(f"Processing time: {elapsed:.2f}s ({real_time_factor:.2f}x real-time)")

        # Prepare info dict
        info_dict = {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": duration,
            "num_segments": len(segments),
            "processing_time": elapsed,
            "real_time_factor": real_time_factor
        }

        return segments, info_dict

    def transcribe_with_speakers(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        language: str = "id",
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Transcribe audio and prepare for speaker diarization.

        This is a convenience method that transcribes and formats
        output for downstream speaker diarization.

        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (optional)
            language: Language code
            progress_callback: Optional progress callback

        Returns:
            Tuple of (segments, info) for diarization
        """
        segments, info = self.transcribe(
            audio_path,
            language=language,
            progress_callback=progress_callback
        )

        info["num_speakers_expected"] = num_speakers

        return segments, info


def transcribe_audio(
    audio_path: str,
    model: str = "large-v3-turbo",
    device: str = "auto",
    language: str = "id",
    beam_size: int = 5,
    vad: bool = True
) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Convenience function for quick transcription.

    Args:
        audio_path: Path to audio file
        model: Whisper model name
        device: Device to use
        language: Language code
        beam_size: Beam size
        vad: Enable VAD

    Returns:
        Tuple of (segments, info)
    """
    transcriber = EnhancedTranscriber()
    return transcriber.transcribe(
        audio_path,
        language=language,
        beam_size=beam_size,
        vad_filter=vad
    )

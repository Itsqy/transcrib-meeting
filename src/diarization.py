"""
Enhanced speaker diarization module with pyannote.audio and resemblyzer.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import time

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

from .utils.config import get_config
from .utils.audio import load_audio_as_wav


logger = logging.getLogger(__name__)


class EnhancedDiarization:
    """
    Speaker diarization with multiple backends.

    Supports:
    - pyannote.audio (state-of-the-art diarization)
    - resemblyzer (speaker embedding + clustering)
    - Hybrid approach (pyannote for segmentation, resemblyzer for embedding)
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize diarization system.

        Args:
            config_path: Optional path to config file
        """
        self.config = get_config(config_path)
        self.method = self.config.get('diarization', 'method')
        self.pyannote_model = None
        self.resemblyzer_encoder = None

        logger.info(f"Diarization method: {self.method}")

    def _load_pyannote_model(self):
        """Load pyannote.audio model."""
        try:
            from pyannote.audio import Pipeline

            hf_token = self.config.get_hf_token()
            if not hf_token:
                logger.warning(
                    "HF_TOKEN not found. Get it at: https://hf.co/settings/tokens\n"
                    "Accept model licenses at:\n"
                    "  - https://hf.co/pyannote/speaker-diarization-3.1\n"
                    "  - https://hf.co/pyannote/segmentation-3.0"
                )
                raise ValueError("HuggingFace token required for pyannote.audio")

            model_name = self.config.get('diarization', 'pyannote', 'model')
            logger.info(f"Loading pyannote.audio model: {model_name}")

            self.pyannote_model = Pipeline.from_pretrained(
                model_name,
                use_auth_token=hf_token
            )

            # Move to GPU if available
            import torch
            if torch.cuda.is_available():
                self.pyannote_model = self.pyannote_model.to(torch.device("cuda"))
                logger.info("pyannote.audio: Using CUDA")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.pyannote_model = self.pyannote_model.to(torch.device("mps"))
                logger.info("pyannote.audio: Using MPS")

            logger.info("pyannote.audio model loaded successfully")

        except ImportError:
            logger.error("pyannote.audio not installed. Install with: pip install pyannote.audio")
            raise
        except Exception as e:
            logger.error(f"Failed to load pyannote.audio: {e}")
            raise

    def _load_resemblyzer_encoder(self):
        """Load resemblyzer encoder."""
        try:
            from resemblyzer import VoiceEncoder

            device = self.config.get('transcription', 'device')
            if device in ['cuda', 'mps']:
                encoder_device = device
            else:
                encoder_device = 'cpu'

            logger.info(f"Loading resemblyzer encoder on {encoder_device}")
            self.resemblyzer_encoder = VoiceEncoder(device=encoder_device)

        except ImportError:
            logger.error("resemblyzer not installed. Install with: pip install resemblyzer")
            raise
        except Exception as e:
            logger.error(f"Failed to load resemblyzer: {e}")
            raise

    def diarize_pyannote(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None
    ) -> List[Dict]:
        """
        Diarize using pyannote.audio.

        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (optional)

        Returns:
            List of diarization segments with start, end, speaker
        """
        if not self.pyannote_model:
            self._load_pyannote_model()

        logger.info(f"Running pyannote.audio diarization on: {audio_path}")

        # Prepare parameters
        kwargs = {}
        if num_speakers:
            kwargs["num_speakers"] = num_speakers

        # Run diarization
        diarization = self.pyannote_model(audio_path, **kwargs)

        # Convert to list of segments
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker
            })

        logger.info(f"pyannote.audio detected {len(set(s['speaker'] for s in segments))} speakers")
        return segments

    def diarize_resemblyzer(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Diarize using resemblyzer embeddings and clustering.

        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers
            segments: Optional pre-segmented audio (e.g., from transcript)

        Returns:
            List of diarization segments with speaker labels
        """
        if not self.resemblyzer_encoder:
            self._load_resemblyzer_encoder()

        logger.info(f"Running resemblyzer diarization on: {audio_path}")

        # Load audio
        wav = load_audio_as_wav(audio_path)
        sample_rate = 16000
        total_duration = len(wav) / sample_rate

        # Extract embeddings using sliding window
        chunk_duration = self.config.get('diarization', 'resemblyzer', 'chunk_duration_sec')
        hop_duration = self.config.get('diarization', 'resemblyzer', 'hop_duration_sec')
        window_duration = self.config.get('diarization', 'resemblyzer', 'window_duration_sec')
        amplitude_threshold = self.config.get('diarization', 'resemblyzer', 'amplitude_threshold')

        embeddings = []
        time_points = []

        for start_t in np.arange(0, total_duration - window_duration, hop_duration):
            s = int(start_t * sample_rate)
            e = int((start_t + window_duration) * sample_rate)
            chunk = wav[s:e]

            # Skip silence
            if np.abs(chunk).mean() < amplitude_threshold:
                continue

            try:
                embedding = self.resemblyzer_encoder.embed_utterance(chunk)
                embeddings.append(embedding)
                time_points.append(start_t + window_duration / 2)
            except Exception as e:
                logger.warning(f"Failed to embed chunk at {start_t:.2f}s: {e}")
                continue

        if not embeddings:
            logger.error("No valid embeddings extracted")
            return []

        embeddings_array = np.array(embeddings)
        logger.info(f"Extracted {len(embeddings)} speaker embeddings")

        # Cluster embeddings
        labels = self._cluster_embeddings(
            embeddings_array,
            num_speakers=num_speakers
        )

        n_speakers = len(set(labels))
        logger.info(f"Detected {n_speakers} speakers")

        # Map speakers to segments
        if segments:
            # Map labels to existing transcript segments
            return self._map_speakers_to_segments(segments, time_points, labels)
        else:
            # Create segments from clustering
            return self._create_segments_from_labels(time_points, labels, window_duration)

    def _cluster_embeddings(
        self,
        embeddings: np.ndarray,
        num_speakers: Optional[int] = None
    ) -> np.ndarray:
        """
        Cluster speaker embeddings.

        Args:
            embeddings: Speaker embedding array
            num_speakers: Expected number of speakers

        Returns:
            Array of cluster labels
        """
        metric = self.config.get('diarization', 'clustering', 'metric')
        linkage = self.config.get('diarization', 'clustering', 'linkage')

        if num_speakers and num_speakers > 1:
            clustering = AgglomerativeClustering(
                n_clusters=num_speakers,
                metric=metric,
                linkage=linkage
            )
            return clustering.fit_predict(embeddings)

        # Auto-detect optimal number of speakers
        min_speakers = self.config.get('diarization', 'clustering', 'min_speakers')
        max_speakers = self.config.get('diarization', 'clustering', 'max_speakers')
        distance_threshold = self.config.get('diarization', 'clustering', 'distance_threshold')

        best_labels = None
        best_score = -1
        best_n = min_speakers

        # Try progressive thresholds
        for threshold in [0.55, 0.45, 0.35, 0.25]:
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=threshold,
                metric=metric,
                linkage=linkage
            )
            labels = clustering.fit_predict(embeddings)
            n = len(set(labels))

            if min_speakers <= n <= max_speakers:
                # Calculate silhouette score
                if n >= 2:
                    score = silhouette_score(embeddings, labels, metric=metric)
                    logger.debug(f"Threshold {threshold}: {n} speakers, score {score:.4f}")

                    if score > best_score:
                        best_score = score
                        best_labels = labels
                        best_n = n
                        if score > 0.4:  # Good enough
                            break

        if best_labels is None:
            # Fallback to default threshold
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=distance_threshold,
                metric=metric,
                linkage=linkage
            )
            best_labels = clustering.fit_predict(embeddings)

        logger.info(f"Selected {best_n} speakers (silhouette score: {best_score:.4f})")
        return best_labels

    def _map_speakers_to_segments(
        self,
        segments: List[Dict],
        time_points: List[float],
        labels: np.ndarray
    ) -> List[Dict]:
        """Map speaker labels to transcript segments."""
        result = []

        for seg in segments:
            mid = (seg["start"] + seg["end"]) / 2
            idx = np.abs(np.array(time_points) - mid).argmin()
            speaker_id = labels[idx]
            seg["speaker"] = f"Speaker {speaker_id + 1}"
            result.append(seg)

        return result

    def _create_segments_from_labels(
        self,
        time_points: List[float],
        labels: np.ndarray,
        window_duration: float
    ) -> List[Dict]:
        """Create diarization segments from labels."""
        segments = []

        for t, label in zip(time_points, labels):
            segments.append({
                "start": max(0, t - window_duration / 2),
                "end": t + window_duration / 2,
                "speaker": f"Speaker {label + 1}"
            })

        return segments

    def diarize(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Run diarization using configured method.

        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (optional)
            segments: Optional transcript segments for mapping

        Returns:
            List of diarization segments with speaker labels
        """
        start_time = time.time()

        if self.method == "pyannote":
            try:
                result = self.diarize_pyannote(audio_path, num_speakers)
            except Exception as e:
                logger.error(f"pyannote.audio failed: {e}")
                logger.info("Falling back to resemblyzer")
                self.method = "resemblyzer"
                result = self.diarize_resemblyzer(audio_path, num_speakers, segments)

        elif self.method == "resemblyzer":
            result = self.diarize_resemblyzer(audio_path, num_speakers, segments)

        elif self.method == "hybrid":
            # Try pyannote first, fallback to resemblyzer
            try:
                result = self.diarize_pyannote(audio_path, num_speakers)
            except Exception as e:
                logger.warning(f"pyannote.audio unavailable: {e}")
                logger.info("Using resemblyzer fallback")
                result = self.diarize_resemblyzer(audio_path, num_speakers, segments)

        else:
            raise ValueError(f"Unknown diarization method: {self.method}")

        elapsed = time.time() - start_time
        logger.info(f"Diarization complete in {elapsed:.2f}s")

        return result


def diarize_audio(
    audio_path: str,
    method: str = "hybrid",
    num_speakers: Optional[int] = None
) -> List[Dict]:
    """
    Convenience function for quick diarization.

    Args:
        audio_path: Path to audio file
        method: Diarization method
        num_speakers: Expected number of speakers

    Returns:
        List of diarization segments
    """
    diarization = EnhancedDiarization()
    return diarization.diarize(audio_path, num_speakers)

"""
Speaker identification and enrollment system.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib

import numpy as np
from scipy.spatial.distance import cosine
from resemblyzer import VoiceEncoder
from tqdm import tqdm

from .utils.config import get_config
from .utils.audio import load_audio_as_wav


logger = logging.getLogger(__name__)


class SpeakerDatabase:
    """
    Speaker profile database for enrollment and identification.

    Stores voice embeddings and metadata for identified speakers.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize speaker database.

        Args:
            config_path: Optional path to config file
        """
        self.config = get_config(config_path)
        self.db_path = self.config.get('speaker_identification', 'database_path')
        self.profiles_path = self.config.get('speaker_identification', 'profiles_path')
        self.threshold = self.config.get('speaker_identification', 'threshold')

        # Create directories
        Path(self.profiles_path).mkdir(parents=True, exist_ok=True)

        # Load database
        self.speakers = self._load_database()

        # Encoder
        self.encoder = None

    def _load_database(self) -> Dict:
        """Load speaker database from JSON file."""
        if Path(self.db_path).exists():
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('speakers', {})
        return {}

    def _save_database(self):
        """Save speaker database to JSON file."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        data = {
            'version': '1.0',
            'speakers': self.speakers,
            'updated_at': datetime.now().isoformat()
        }

        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_encoder(self):
        """Lazy-load voice encoder."""
        if self.encoder is None:
            device = self.config.get('transcription', 'device')
            if device in ['cuda', 'mps']:
                encoder_device = device
            else:
                encoder_device = 'cpu'

            logger.info(f"Loading voice encoder on {encoder_device}")
            self.encoder = VoiceEncoder(device=encoder_device)

        return self.encoder

    def _compute_embedding(self, audio_path: str) -> np.ndarray:
        """
        Compute speaker embedding from audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Speaker embedding vector
        """
        wav = load_audio_as_wav(audio_path)
        encoder = self._get_encoder()
        return encoder.embed_utterance(wav)

    def _compute_embedding_from_array(self, wav: np.ndarray) -> np.ndarray:
        """
        Compute speaker embedding from audio array.

        Args:
            wav: Audio array

        Returns:
            Speaker embedding vector
        """
        encoder = self._get_encoder()
        return encoder.embed_utterance(wav)

    def enroll(
        self,
        name: str,
        sample_paths: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Enroll a new speaker from voice samples.

        Args:
            name: Speaker name/identifier
            sample_paths: List of paths to voice sample files (3-10 recommended)
            metadata: Optional metadata (title, department, etc.)

        Returns:
            Enrollment result with success status and info
        """
        min_samples = self.config.get('speaker_identification', 'enrollment_min_samples')
        max_samples = self.config.get('speaker_identification', 'enrollment_max_samples')

        if len(sample_paths) < min_samples:
            return {
                'success': False,
                'error': f'Minimum {min_samples} samples required, got {len(sample_paths)}'
            }

        if len(sample_paths) > max_samples:
            return {
                'success': False,
                'error': f'Maximum {max_samples} samples allowed, got {len(sample_paths)}'
            }

        if name in self.speakers:
            return {
                'success': False,
                'error': f'Speaker "{name}" already enrolled. Use update_enrollment() to modify.'
            }

        logger.info(f"Enrolling speaker: {name} ({len(sample_paths)} samples)")

        # Compute embeddings from all samples
        embeddings = []
        valid_samples = []

        for sample_path in tqdm(sample_paths, desc=f"Processing {name}"):
            if not Path(sample_path).exists():
                logger.warning(f"Sample not found: {sample_path}")
                continue

            try:
                embedding = self._compute_embedding(sample_path)
                embeddings.append(embedding)
                valid_samples.append(sample_path)
            except Exception as e:
                logger.warning(f"Failed to process {sample_path}: {e}")

        if len(embeddings) < min_samples:
            return {
                'success': False,
                'error': f'Only {len(embeddings)} valid samples processed (need {min_samples})'
            }

        # Average embeddings to create profile
        profile_embedding = np.mean(embeddings, axis=0)

        # Normalize
        profile_embedding = profile_embedding / np.linalg.norm(profile_embedding)

        # Generate profile ID
        profile_id = hashlib.md5(f"{name}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]

        # Create speaker profile
        speaker_data = {
            'id': profile_id,
            'name': name,
            'embedding': profile_embedding.tolist(),
            'num_samples': len(embeddings),
            'sample_paths': valid_samples,
            'created_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }

        # Save to database
        self.speakers[name] = speaker_data
        self._save_database()

        logger.info(f"Successfully enrolled: {name} (ID: {profile_id})")

        return {
            'success': True,
            'speaker': name,
            'id': profile_id,
            'num_samples': len(embeddings)
        }

    def update_enrollment(
        self,
        name: str,
        additional_samples: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Update existing speaker enrollment.

        Args:
            name: Speaker name
            additional_samples: Additional voice samples to add
            metadata: Updated metadata

        Returns:
            Update result
        """
        if name not in self.speakers:
            return {
                'success': False,
                'error': f'Speaker "{name}" not found in database'
            }

        speaker_data = self.speakers[name]

        # Update metadata
        if metadata:
            speaker_data['metadata'].update(metadata)

        # Add new samples
        if additional_samples:
            logger.info(f"Adding {len(additional_samples)} samples to {name}")

            current_embedding = np.array(speaker_data['embedding'])
            num_existing = speaker_data['num_samples']

            new_embeddings = []
            valid_samples = []

            for sample_path in additional_samples:
                if not Path(sample_path).exists():
                    continue

                try:
                    embedding = self._compute_embedding(sample_path)
                    new_embeddings.append(embedding)
                    valid_samples.append(sample_path)
                except Exception as e:
                    logger.warning(f"Failed to process {sample_path}: {e}")

            if new_embeddings:
                # Recombine with existing embedding
                total_samples = num_existing + len(new_embeddings)
                new_profile = (current_embedding * num_existing + np.mean(new_embeddings, axis=0) * len(new_embeddings)) / total_samples
                new_profile = new_profile / np.linalg.norm(new_profile)

                speaker_data['embedding'] = new_profile.tolist()
                speaker_data['num_samples'] = total_samples
                speaker_data['sample_paths'].extend(valid_samples)

        speaker_data['updated_at'] = datetime.now().isoformat()
        self._save_database()

        return {
            'success': True,
            'speaker': name,
            'num_samples': speaker_data['num_samples']
        }

    def identify(
        self,
        embedding: np.ndarray,
        threshold: Optional[float] = None
    ) -> Tuple[Optional[str], float]:
        """
        Identify speaker from embedding.

        Args:
            embedding: Speaker embedding to identify
            threshold: Similarity threshold (default from config)

        Returns:
            Tuple of (speaker_name, confidence_score) or (None, 0) if no match
        """
        if not self.speakers:
            return None, 0.0

        if threshold is None:
            threshold = self.threshold

        # Normalize query embedding
        embedding = embedding / np.linalg.norm(embedding)

        best_match = None
        best_score = threshold

        for name, speaker_data in self.speakers.items():
            profile_embedding = np.array(speaker_data['embedding'])

            # Compute cosine similarity
            similarity = 1 - cosine(embedding, profile_embedding)

            if similarity > best_score:
                best_match = name
                best_score = similarity

        return best_match, best_score

    def identify_from_audio(
        self,
        audio_path: str,
        threshold: Optional[float] = None
    ) -> Tuple[Optional[str], float]:
        """
        Identify speaker from audio file.

        Args:
            audio_path: Path to audio file
            threshold: Similarity threshold

        Returns:
            Tuple of (speaker_name, confidence_score)
        """
        embedding = self._compute_embedding(audio_path)
        return self.identify(embedding, threshold)

    def list_speakers(self) -> List[Dict]:
        """
        List all enrolled speakers.

        Returns:
            List of speaker info dicts
        """
        speakers = []

        for name, data in self.speakers.items():
            speakers.append({
                'name': name,
                'id': data['id'],
                'num_samples': data['num_samples'],
                'created_at': data['created_at'],
                'metadata': data.get('metadata', {})
            })

        return speakers

    def remove_speaker(self, name: str) -> bool:
        """
        Remove speaker from database.

        Args:
            name: Speaker name to remove

        Returns:
            True if removed, False if not found
        """
        if name in self.speakers:
            del self.speakers[name]
            self._save_database()
            logger.info(f"Removed speaker: {name}")
            return True
        return False

    def get_speaker_info(self, name: str) -> Optional[Dict]:
        """
        Get detailed information about a speaker.

        Args:
            name: Speaker name

        Returns:
            Speaker info dict or None
        """
        return self.speakers.get(name)

    def get_embedding(self, name: str) -> Optional[np.ndarray]:
        """
        Get speaker embedding.

        Args:
            name: Speaker name

        Returns:
            Embedding array or None
        """
        data = self.speakers.get(name)
        if data:
            return np.array(data['embedding'])
        return None


def batch_identify(
    embeddings: List[np.ndarray],
    database: SpeakerDatabase,
    threshold: Optional[float] = None
) -> List[Tuple[Optional[str], float]]:
    """
    Identify multiple embeddings.

    Args:
        embeddings: List of speaker embeddings
        database: Speaker database
        threshold: Similarity threshold

    Returns:
        List of (speaker_name, confidence) tuples
    """
    results = []

    for embedding in embeddings:
        speaker, confidence = database.identify(embedding, threshold)
        results.append((speaker, confidence))

    return results

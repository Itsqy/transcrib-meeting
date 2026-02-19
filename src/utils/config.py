"""
Configuration loader and manager for the transcription system.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Default configuration
DEFAULT_CONFIG = {
    'transcription': {
        'model': 'large-v3-turbo',
        'device': 'auto',
        'compute_type': 'auto',
        'language': 'id',
        'beam_size': 5,
        'vad': {
            'enabled': True,
            'min_speech_duration_ms': 500,
            'min_silence_duration_ms': 1000,
            'speech_pad_ms': 400,
        }
    },
    'diarization': {
        'method': 'hybrid',
        'clustering': {
            'distance_threshold': 0.55,
            'metric': 'cosine',
            'linkage': 'average',
            'min_speakers': 2,
            'max_speakers': 15,
        }
    },
    'speaker_identification': {
        'enabled': True,
        'database_path': 'speakers/database.json',
        'threshold': 0.80,
        'enrollment_min_samples': 3,
        'enrollment_max_samples': 10,
        'profiles_path': 'speakers/profiles',
    },
    'summarization': {
        'enabled': True,
        'provider': 'openai',
        'openai': {
            'model': 'gpt-4o-mini',
            'api_key': None,
            'temperature': 0.3,
            'max_tokens': 2000,
        },
        'language': 'id',
    },
    'output': {
        'directory': 'output',
        'include_timestamps': True,
        'formats': ['md'],
        'paragraph_sentences': 6,
        'include_summary': True,
        'include_action_items': True,
    },
    'logging': {
        'level': 'INFO',
        'file': None,
    }
}


class Config:
    """Configuration manager for the transcription system."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config YAML file. If None, uses default config.
        """
        self.config = DEFAULT_CONFIG.copy()
        self._load_env()

        if config_path and os.path.exists(config_path):
            self._load_yaml(config_path)

        # Apply device auto-detection
        self._apply_device_detection()

    def _load_env(self):
        """Load environment variables from .env file."""
        load_dotenv()
        self.env = {
            'HF_TOKEN': os.getenv('HF_TOKEN'),
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        }

    def _load_yaml(self, config_path: str):
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                self._merge_config(self.config, yaml_config)

    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge override config into base config."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _apply_device_detection(self):
        """
        Auto-detect and set the best available device.

        Note: faster-whisper doesn't support MPS (Apple Silicon) yet, so we use CPU.
        For MPS support, consider using the original OpenAI Whisper model.
        """
        import torch

        device = self.config['transcription']['device']
        compute_type = self.config['transcription']['compute_type']

        if device == 'auto':
            if torch.cuda.is_available():
                device = 'cuda'
                compute_type = 'float16' if compute_type == 'auto' else compute_type
            else:
                # MPS (Apple Silicon) is not supported by faster-whisper yet
                # Fall back to CPU with int8 quantization
                device = 'cpu'
                compute_type = 'int8' if compute_type == 'auto' else compute_type

        self.config['transcription']['device'] = device
        self.config['transcription']['compute_type'] = compute_type

    def get(self, *keys, default=None) -> Any:
        """
        Get configuration value by nested keys.

        Args:
            *keys: Nested keys to access the value
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            config.get('transcription', 'model')
            config.get('diarization', 'clustering', 'metric')
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, *keys, value: Any):
        """
        Set configuration value by nested keys.

        Args:
            *keys: Nested keys to access the value
            value: Value to set

        Example:
            config.set('transcription', 'beam_size', value=7)
        """
        config_ref = self.config
        for key in keys[:-1]:
            if key not in config_ref:
                config_ref[key] = {}
            config_ref = config_ref[key]
        config_ref[keys[-1]] = value

    def get_hf_token(self) -> Optional[str]:
        """Get HuggingFace token from config or environment."""
        token = self.get('diarization', 'pyannote', 'hf_token')
        return token or self.env.get('HF_TOKEN')

    def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from config or environment."""
        key = self.get('summarization', 'openai', 'api_key')
        return key or self.env.get('OPENAI_API_KEY')

    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.get('output', 'directory'),
            self.get('speaker_identification', 'profiles_path'),
            os.path.dirname(self.get('speaker_identification', 'database_path')),
        ]

        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)


# Global config instance
_global_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get or create global configuration instance.

    Args:
        config_path: Path to config file (only used on first call).
                    If None, tries default location 'config/config.yaml'

    Returns:
        Config instance
    """
    global _global_config
    if _global_config is None:
        # Use default config path if not provided
        if config_path is None:
            # Try to find config.yaml in standard locations
            for possible_path in ['config/config.yaml', './config.yaml']:
                if os.path.exists(possible_path):
                    config_path = possible_path
                    break
        _global_config = Config(config_path)
    return _global_config


def reset_config():
    """Reset global configuration instance (mainly for testing)."""
    global _global_config
    _global_config = None

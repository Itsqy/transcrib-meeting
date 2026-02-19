"""
AI-powered meeting summarization module.
Supports OpenAI GPT and local LLMs.
"""
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .utils.config import get_config


logger = logging.getLogger(__name__)


class MeetingSummarizer:
    """
    AI-powered meeting summarization with structured output.

    Generates:
    - Executive summary
    - Key topics discussed
    - Decisions made
    - Action items (Task, PIC, Deadline)
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize summarizer.

        Args:
            config_path: Optional path to config file
        """
        self.config = get_config(config_path)
        self.provider = self.config.get('summarization', 'provider')
        self.language = self.config.get('summarization', 'language', default='id')

        # Initialize client
        self._init_client()

    def _init_client(self):
        """Initialize AI client based on provider."""
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "local":
            self._init_local_llm()
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI

            api_key = self.config.get_openai_api_key()
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in config or environment")

            self.client = OpenAI(api_key=api_key)
            self.model = self.config.get('summarization', 'openai', 'model')
            self.temperature = self.config.get('summarization', 'openai', 'temperature')
            self.max_tokens = self.config.get('summarization', 'openai', 'max_tokens')

            logger.info(f"OpenAI client initialized: {self.model}")

        except ImportError:
            logger.error("OpenAI package not installed. Install with: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            raise

    def _init_local_llm(self):
        """Initialize local LLM client (Ollama, etc.)."""
        try:
            import requests

            self.model = self.config.get('summarization', 'local', 'model')
            self.base_url = self.config.get('summarization', 'local', 'base_url')
            self.temperature = self.config.get('summarization', 'local', 'temperature')

            # Test connection
            try:
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if response.status_code != 200:
                    logger.warning(
                        f"Local LLM server may not be running at {self.base_url}. "
                        f"Start Ollama with: ollama serve"
                    )
            except requests.exceptions.ConnectionError:
                logger.warning(
                    f"Cannot connect to local LLM at {self.base_url}. "
                    f"Make sure Ollama is running: ollama serve"
                )
            except requests.exceptions.Timeout:
                logger.warning(
                    f"Connection to local LLM at {self.base_url} timed out. "
                    f"Check if Ollama is running."
                )

            logger.info(f"Local LLM client initialized: {self.model} at {self.base_url}")

        except ImportError:
            logger.error("Requests package not installed. Install with: pip install requests")
            raise

    def _create_prompt(self, transcript: str, speakers: Optional[List[str]] = None) -> str:
        """
        Create summarization prompt.

        Args:
            transcript: Meeting transcript
            speakers: List of speaker names

        Returns:
            Formatted prompt
        """
        lang_instruction = "Indonesia" if self.language == 'id' else "Inggris"

        prompt = f"""Analisis transkrip rapat berikut dan buat rangkuman terstruktur dalam bahasa {lang_instruction}.

Transkrip:
{transcript}

Buat rangkuman dengan format JSON berikut:
{{
  "executive_summary": "Ringkasan eksekutif 2-3 kalimat",
  "key_topics": ["Topik 1", "Topik 2", "Topik 3"],
  "discussion_points": [
    {{
      "topic": "Topik utama",
      "timestamp_start": "HH:MM",
      "timestamp_end": "HH:MM",
      "sub_points": [
        {{
          "point": "Sub-poin utama",
          "details": "Detail penjelasan tentang sub-poin ini",
          "speaker": "Nama pembicara (jika relevan)"
        }}
      ]
    }}
  ],
  "decisions": [
    {{"topic": "Topik", "decision": "Keputusan yang dibuat", "by": "Pihak yang memutuskan"}}
  ],
  "action_items": [
    {{"task": "Deskripsi tugas", "pic": "Penanggung jawab", "deadline": "Batas waktu (jika ada)", "priority": "tinggi/sedang/rendah"}}
  ],
  "next_meeting": "Tanggal/jadwal rapat berikutnya (jika disebutkan)"
}}

Petunjuk:
- Executive summary: capture poin utama secara ringkas
- Key topics: daftar topik utama yang dibahas (3-7 items)
- Discussion points: struktur hierarkis dengan:
  * topic: topik utama yang dibahas
  * timestamp_start dan timestamp_end: estimasi waktu pembahasan (jika bisa diperkirakan dari transkrip)
  * sub_points: daftar sub-poin dengan detail penjelasan
- Decisions: keputusan penting yang dibuat beserta konteksnya
- Action items: tugas konkret dengan PIC (Person In Charge) yang jelas
- Kelompokkan pembahasan berdasarkan topik meskipun pembicaraan melompat antar topik
- Jika informasi tidak tersedia, gunakan null atau string kosong
- Gunakan nama pembicara asli dari transkrip untuk PIC

Output HANYA JSON valid, tanpa teks tambahan."""

        return prompt

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional meeting assistant that creates structured summaries in Indonesian or English."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        return response.choices[0].message.content

    def _call_local_llm(self, prompt: str, max_retries: int = 3) -> str:
        """
        Call local LLM API with retry logic.

        Args:
            prompt: The prompt to send to the LLM
            max_retries: Maximum number of retry attempts

        Returns:
            LLM response text

        Raises:
            Exception: If all retries fail
        """
        import requests

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling local LLM (attempt {attempt + 1}/{max_retries})...")

                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=300  # 5 minutes timeout for long transcripts
                )

                response.raise_for_status()
                data = response.json()
                result = data.get("response", "")

                if not result:
                    raise ValueError("Empty response from local LLM")

                logger.info("Local LLM response received successfully")
                return result

            except requests.exceptions.ConnectionError as e:
                last_error = e
                logger.error(
                    f"Failed to connect to Ollama at {self.base_url}. "
                    f"Make sure Ollama is running: ollama serve"
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

            except requests.exceptions.Timeout as e:
                last_error = e
                logger.error(
                    f"Request to Ollama timed out. "
                    f"The model may still be loading or the transcript is too long."
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

            except requests.exceptions.HTTPError as e:
                last_error = e
                logger.error(f"HTTP error from Ollama: {e}")

                if response.status_code == 404:
                    logger.error(
                        f"Model '{self.model}' not found. "
                        f"Download it with: ollama pull {self.model}"
                    )
                    break  # Don't retry for 404 errors
                elif response.status_code == 500:
                    # Server error, may be worth retrying
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error calling local LLM: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        # All retries failed
        error_msg = (
            f"Failed to call local LLM after {max_retries} attempts. "
            f"Last error: {last_error}"
        )
        logger.error(error_msg)

        raise Exception(error_msg)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse AI response into structured summary.

        Args:
            response: Raw AI response

        Returns:
            Parsed summary dict
        """
        # Try to extract JSON from response
        response = response.strip()

        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])

        try:
            summary = json.loads(response)
            return summary
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, returning raw text")

            # Fallback: create basic structure
            return {
                "executive_summary": response[:500],
                "key_topics": [],
                "decisions": [],
                "action_items": [],
                "next_meeting": None,
                "raw_response": response
            }

    def summarize(
        self,
        transcript: str,
        speakers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate meeting summary from transcript.

        Args:
            transcript: Meeting transcript text
            speakers: Optional list of speaker names

        Returns:
            Summary dict with executive summary, topics, decisions, action items
        """
        logger.info("Generating meeting summary...")

        # Check if summarization is enabled
        if not self.config.get('summarization', 'enabled'):
            logger.info("Summarization disabled in config")
            return self._empty_summary()

        # Truncate transcript if too long
        max_length = 12000  # Approx token limit
        if len(transcript) > max_length:
            logger.warning(f"Transcript too long ({len(transcript)} chars), truncating to {max_length}")
            transcript = transcript[:max_length] + "\n\n[Transkrip dipotong karena terlalu panjang...]"

        # Create prompt
        prompt = self._create_prompt(transcript, speakers)

        # Call AI
        try:
            if self.provider == "openai":
                response = self._call_openai(prompt)
            else:
                response = self._call_local_llm(prompt)

            # Parse response
            summary = self._parse_response(response)

            # Add metadata
            summary["generated_at"] = datetime.now().isoformat()
            summary["provider"] = self.provider
            summary["model"] = self.model
            summary["language"] = self.language

            logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return {
                "executive_summary": "Gagal membuat ringkasan otomatis.",
                "key_topics": [],
                "decisions": [],
                "action_items": [],
                "error": str(e)
            }

    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary structure."""
        return {
            "executive_summary": "",
            "key_topics": [],
            "decisions": [],
            "action_items": [],
            "next_meeting": None
        }

    def format_summary_markdown(self, summary: Dict[str, Any]) -> str:
        """
        Format summary as Markdown.

        Args:
            summary: Summary dict

        Returns:
            Formatted Markdown string
        """
        lines = []

        lines.append("## 📊 Ringkasan Rapat")
        lines.append("")

        # Executive summary
        if summary.get("executive_summary"):
            lines.append("### Ringkasan Eksekutif")
            lines.append(summary["executive_summary"])
            lines.append("")

        # Key topics
        if summary.get("key_topics"):
            lines.append("### 📌 Topik Utama")
            for topic in summary["key_topics"]:
                lines.append(f"- {topic}")
            lines.append("")

        # Decisions
        if summary.get("decisions"):
            lines.append("### ✅ Keputusan")
            for decision in summary["decisions"]:
                topic = decision.get("topic", "-")
                decision_text = decision.get("decision", "-")
                by = decision.get("by", "")
                if by:
                    lines.append(f"- **{topic}**: {decision_text} (oleh {by})")
                else:
                    lines.append(f"- **{topic}**: {decision_text}")
            lines.append("")

        # Action items
        if summary.get("action_items"):
            lines.append("### 📋 Action Items")
            lines.append("")
            lines.append("| Tugas | PIC | Deadline | Prioritas |")
            lines.append("|-------|-----|----------|-----------|")

            for item in summary["action_items"]:
                task = item.get("task", "-")
                pic = item.get("pic", "-")
                deadline = item.get("deadline", "-")
                priority = item.get("priority", "sedang")
                lines.append(f"| {task} | {pic} | {deadline} | {priority} |")

            lines.append("")

        # Next meeting
        if summary.get("next_meeting"):
            lines.append(f"### 📅 Rapat Berikutnya")
            lines.append(summary["next_meeting"])
            lines.append("")

        return "\n".join(lines)


def summarize_meeting(
    transcript: str,
    provider: str = "openai",
    language: str = "id"
) -> Dict[str, Any]:
    """
    Convenience function for quick summarization.

    Args:
        transcript: Meeting transcript
        provider: AI provider
        language: Summary language

    Returns:
        Summary dict
    """
    summarizer = MeetingSummarizer()
    return summarizer.summarize(transcript)

"""
Converts transcript_speakers.txt into a clean, professional Markdown file.
Groups consecutive same-speaker segments into readable paragraphs (~5 sentences each).

Enhanced with:
- Named speakers support (Pak Budi, Ibu Siti, etc.)
- AI-powered meeting summaries
- Action items table
"""
import re
import os
import json
from datetime import datetime


SPEAKER_STYLES = {
    "Speaker 1": "🔵",
    "Speaker 2": "🟢",
    "Speaker 3": "🟠",
    "Speaker 4": "🟣",
    "Speaker 5": "🔴",
    "Speaker 6": "🟡",
}

MAX_SENTENCES_PER_PARAGRAPH = 6


def load_speaker_mapping():
    """Load speaker name mapping from speaker_mapping.json if exists."""
    mapping_file = "speaker_mapping.json"
    if os.path.exists(mapping_file):
        with open(mapping_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_summary():
    """Load AI summary from summary.json if exists."""
    summary_file = "summary.json"
    if os.path.exists(summary_file):
        with open(summary_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def parse_transcript(filepath):
    """Parse transcript_speakers.txt into structured blocks."""
    blocks = []
    current_speaker = None
    current_block = None

    # Load speaker name mapping
    speaker_mapping = load_speaker_mapping()

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if not line:
                continue

            # Support both "Speaker X" and custom names
            speaker_match = re.match(r'^--- (.+?) ---$', line)
            if speaker_match:
                if current_block:
                    blocks.append(current_block)

                speaker_label = speaker_match.group(1)
                # Use mapped name if available
                display_name = speaker_mapping.get(speaker_label, speaker_label)

                current_speaker = speaker_label
                current_block = {
                    "speaker": display_name,
                    "speaker_label": speaker_label,  # Keep original for consistency
                    "start": None,
                    "end": None,
                    "segments": []
                }
                continue

            seg_match = re.match(
                r'\s*\[(\d+:\d+(?::\d+)?) - (\d+:\d+(?::\d+)?)\]\s*(.*)',
                line
            )
            if seg_match and current_block is not None:
                start, end, text = seg_match.groups()
                if current_block["start"] is None:
                    current_block["start"] = start
                current_block["end"] = end
                if text.strip():
                    current_block["segments"].append({
                        "start": start,
                        "end": end,
                        "text": text.strip()
                    })

    if current_block:
        blocks.append(current_block)

    return blocks


def build_markdown(blocks, audio_filename, summary=None):
    """Build clean Markdown from parsed blocks."""
    lines = []

    # Header
    lines.append("# 📋 Transkrip Rapat")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(f"| **File Audio** | `{audio_filename}` |")

    if blocks:
        last_end = blocks[-1]["end"]
        lines.append(f"| **Durasi** | `{last_end}` |")

    speakers = sorted(set(b["speaker"] for b in blocks))
    # Use emoji for generic speakers, just name for identified speakers
    speaker_legend = ", ".join(
        f"{SPEAKER_STYLES.get(s, '👤')} {s}" if s.startswith("Speaker ") else s
        for s in speakers
    )
    lines.append(f"| **Pembicara** | {len(speakers)} orang |")
    lines.append(f"| **Tanggal Transkrip** | {datetime.now().strftime('%d %B %Y')} |")
    lines.append("")

    # Only show legend if there are generic speakers
    if any(s.startswith("Speaker ") for s in speakers):
        lines.append(f"**Keterangan:** {speaker_legend}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # AI Summary section
    if summary:
        lines.append(format_summary(summary))
        lines.append("")
        lines.append("---")
        lines.append("")

    # Body
    for block in blocks:
        speaker = block["speaker"]
        icon = SPEAKER_STYLES.get(speaker, "👤")
        start = block["start"]
        end = block["end"]

        if not block["segments"]:
            continue

        # Speaker header
        lines.append(f"### {icon} {speaker} &nbsp;•&nbsp; `{start} – {end}`")
        lines.append("")

        # Split segments into paragraphs of N sentences
        segments = block["segments"]
        for i in range(0, len(segments), MAX_SENTENCES_PER_PARAGRAPH):
            chunk = segments[i:i + MAX_SENTENCES_PER_PARAGRAPH]
            ts_start = chunk[0]["start"]
            ts_end = chunk[-1]["end"]
            text = " ".join(seg["text"] for seg in chunk)

            lines.append(f"**`{ts_start}`** — {text}")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(
        "*Transkrip ini dihasilkan secara otomatis menggunakan AI "
        "(Whisper large-v3-turbo + pyannote.audio/resemblyzer). "
        "Akurasi bergantung pada kualitas audio.*"
    )

    return "\n".join(lines)


def format_summary(summary):
    """Format AI summary as Markdown."""
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


def main():
    # Use the refined version if available, otherwise fallback to raw
    input_file = "transcript_speakers_refined.txt"
    if not os.path.exists(input_file):
        input_file = "transcript_speakers.txt"

    output_file = "transcript.md"
    audio_file = "audio.m4a"

    if not os.path.exists(input_file):
        print(f"ERROR: {input_file} not found")
        return

    print(f"[1/3] Parsing {input_file}...")
    blocks = parse_transcript(input_file)
    print(f"  Found {len(blocks)} speaking turns")

    print(f"[2/3] Loading AI summary...")
    summary = load_summary()
    if summary:
        print(f"  Summary found: {summary.get('provider', 'unknown')} / {summary.get('model', 'unknown')}")
    else:
        print(f"  No summary found (summary.json)")

    print(f"[3/3] Building Markdown...")
    md = build_markdown(blocks, audio_file, summary)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\n✅ Saved to: {output_file}")
    print(f"   Total: {len(md)} characters")


if __name__ == "__main__":
    main()

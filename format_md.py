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
MIN_SEGMENT_LENGTH = 80  # Minimum characters before starting a new "sentence"
MAX_SENTENCE_LENGTH = 600  # Maximum characters for a single sentence (prevent overly long)
MIN_SENTENCE_END_CHARS = ['.', '!', '?', ',', ';']  # Characters that indicate potential end


def build_sentences(segments):
    """
    Combine consecutive short segments into coherent sentences.
    Groups fragments until we have a complete thought or reach minimum length.
    More aggressive combining for better readability.
    """
    if not segments:
        return []

    sentences = []
    current_sentence = {
        "segments": [],
        "text": [],
    }

    for i, seg in enumerate(segments):
        text = seg["text"].strip()

        # Skip empty segments
        if not text:
            continue

        # Look ahead to check if we should combine with next segment
        next_text = None
        if i + 1 < len(segments):
            next_text = segments[i + 1]["text"].strip()

        # Add to current sentence
        current_sentence["segments"].append(seg)
        current_sentence["text"].append(text)

        combined_text = " ".join(current_sentence["text"])
        text_length = len(combined_text)

        # Check if we should end the sentence
        end_sentence = False

        # Hard cap - never exceed maximum length
        if text_length >= MAX_SENTENCE_LENGTH:
            end_sentence = True
        # Strong terminators - only end if sentence is substantial length
        elif text and text[-1] in ['!', '?']:
            # Keep combining if very short
            if text_length >= MIN_SEGMENT_LENGTH:
                end_sentence = True
            # Or if next is a new topic (starts with capital and we have some content)
            elif next_text and next_text[0].isupper() and len(current_sentence["text"]) > 2:
                end_sentence = True
        # Period - end if sentence is long enough
        elif text and text[-1] == '.':
            if text_length >= MIN_SEGMENT_LENGTH:
                end_sentence = True
            # Or if next segment starts with capital (likely new sentence)
            elif next_text and next_text[0].isupper() and len(current_sentence["text"]) > 1:
                end_sentence = True
        # Comma or other - continue unless we're very long
        elif text and text[-1] in [',', ';', ':']:
            if text_length >= MIN_SEGMENT_LENGTH * 2.5:
                end_sentence = True
        # No clear ending - check length
        elif text_length >= MIN_SEGMENT_LENGTH * 2:
            # End if next starts with capital and current is substantial
            if next_text and next_text[0].isupper() and len(current_sentence["text"]) > 1:
                end_sentence = True

        if end_sentence:
            # Save the sentence
            sentences.append({
                "start": current_sentence["segments"][0]["start"],
                "end": current_sentence["segments"][-1]["end"],
                "text": " ".join(current_sentence["text"])
            })
            # Reset
            current_sentence = {"segments": [], "text": []}

    # Add any remaining text
    if current_sentence["text"]:
        sentences.append({
            "start": current_sentence["segments"][0]["start"],
            "end": current_sentence["segments"][-1]["end"],
            "text": " ".join(current_sentence["text"])
        })

    return sentences


def load_speaker_mapping():
    """Load speaker name mapping from speaker_mapping.json if exists."""
    mapping_file = "speaker_mapping.json"
    if os.path.exists(mapping_file):
        with open(mapping_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_summary(output_base="transcript"):
    """Load AI summary from {output_base}_summary.json if exists."""
    summary_file = f"{output_base}_summary.json"
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

        # Build sentences by combining consecutive segments
        # Groups short fragments into complete sentences
        sentences = build_sentences(block["segments"])

        for sentence_data in sentences:
            ts_start = sentence_data["start"]
            ts_end = sentence_data["end"]
            text = sentence_data["text"].strip()

            if text:
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

    # Discussion Points (Hierarchical structure)
    discussion_points = summary.get('discussion_points', [])
    if discussion_points and isinstance(discussion_points, list):
        lines.append("### 🔍 Pembahasan Detail")

        for topic_data in discussion_points:
            if isinstance(topic_data, dict):
                topic = topic_data.get('topic', 'Topik tanpa judul')
                ts_start = topic_data.get('timestamp_start', '')
                ts_end = topic_data.get('timestamp_end', '')

                # Topic header with timestamp
                lines.append(f"#### 📌 {topic}")
                if ts_start and ts_end:
                    lines.append(f"*{ts_start} - {ts_end}*")
                lines.append("")

                # Sub-points
                sub_points = topic_data.get('sub_points', [])
                if sub_points and isinstance(sub_points, list):
                    for sp in sub_points:
                        if isinstance(sp, dict):
                            point = sp.get('point', '')
                            details = sp.get('details', '')
                            speaker = sp.get('speaker', '')

                            if point:
                                if details:
                                    lines.append(f"- **{point}**: {details}")
                                else:
                                    lines.append(f"- **{point}**")
                                if speaker and speaker != 'null':
                                    lines.append(f"  _— {speaker}_")
                lines.append("")

    # Key topics (fallback if no discussion_points)
    elif summary.get("key_topics"):
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
    import sys

    # Get output base from command line or use default
    output_base = sys.argv[1] if len(sys.argv) > 1 else "transcript"

    # Use the refined version if available, otherwise fallback to raw
    input_file = f"{output_base}_speakers_refined.txt"
    if not os.path.exists(input_file):
        input_file = f"{output_base}_speakers.txt"

    output_file = f"{output_base}.md"
    audio_file = f"{output_base}.m4a"

    if not os.path.exists(input_file):
        print(f"ERROR: {input_file} not found")
        return

    print(f"[1/3] Parsing {input_file}...")
    blocks = parse_transcript(input_file)
    print(f"  Found {len(blocks)} speaking turns")

    print(f"[2/3] Loading AI summary...")
    summary = load_summary(output_base)
    if summary:
        print(f"  Summary found: {summary.get('provider', 'unknown')} / {summary.get('model', 'unknown')}")
    else:
        print(f"  No summary found ({output_base}_summary.json)")

    print(f"[3/3] Building Markdown...")
    md = build_markdown(blocks, audio_file, summary)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\n✅ Saved to: {output_file}")
    print(f"   Total: {len(md)} characters")


if __name__ == "__main__":
    main()

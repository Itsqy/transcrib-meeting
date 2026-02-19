#!/usr/bin/env python3
"""
Generate clean, copy-paste friendly summary markdown file.
Reads from summary.json and creates summary.md
"""
import json
import os
import sys
from datetime import datetime


def clean_json_string(text):
    """
    Attempt to clean malformed JSON from LLM responses.
    Removes common artifacts like trailing commas, incomplete blocks, etc.
    """
    # If it's not a string, return as-is
    if not isinstance(text, str):
        return text

    # Try to find the first complete JSON object
    text = text.strip()

    # Find first { and last }
    first_brace = text.find('{')
    last_brace = text.rfind('}')

    if first_brace == -1 or last_brace == -1:
        return text

    # Extract the JSON portion
    json_text = text[first_brace:last_brace + 1]

    # Remove trailing commas before closing brackets/braces
    json_text = json_text.replace(',\n}', '\n}')
    json_text = json_text.replace(',\n]', '\n]')
    json_text = json_text.replace(',}', '}')
    json_text = json_text.replace(',]', ']')

    # Remove incomplete ```json blocks
    json_text = json_text.replace('```json', '')
    json_text = json_text.replace('```', '')

    return json_text


def extract_value_from_json_string(json_str, key):
    """Extract a specific value from a JSON-like string."""
    try:
        # Pattern to find "key": "value" or "key": "value with spaces"
        import re
        pattern = rf'"{key}"\s*:\s*"([^"]*(?:\\.[^"]*)*)"'
        match = re.search(pattern, json_str)
        if match:
            # Decode escaped characters
            value = match.group(1)
            value = value.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
            return value
    except:
        pass
    return None


def extract_array_from_json_string(json_str, key):
    """Extract an array from a JSON-like string."""
    try:
        import re
        # Find the array content after "key": [
        pattern = rf'"{key}"\s*:\s*\[(.*?)\](?=\s*[,}}])'
        match = re.search(pattern, json_str, re.DOTALL)

        if match:
            array_content = match.group(1)

            # First, check if it's an array of objects (contains {)
            if '{' in array_content:
                # Extract objects from the array
                items = []

                # Find all {...} objects within the array
                obj_pattern = r'\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
                for obj_match in re.finditer(obj_pattern, array_content):
                    obj_str = obj_match.group(0)
                    # Extract fields from the object
                    item = {}
                    for field in ['task', 'pic', 'deadline', 'priority', 'topic', 'decision', 'by']:
                        value = extract_value_from_json_string(obj_str, field)
                        if value:
                            item[field] = value
                    if item:
                        items.append(item)

                return items
            else:
                # Array of strings - extract quoted values
                items = []
                # Find all quoted strings in the array
                str_pattern = r'"([^"\\]*(?:\\.[^"\\]*)*)"'
                for str_match in re.finditer(str_pattern, array_content):
                    value = str_match.group(1)
                    # Decode escaped characters
                    value = value.replace('\\"', '"').replace('\\n', '\n')
                    if value:
                        items.append(value)
                return items
    except Exception as e:
        pass
    return None


def parse_nested_summary(summary):
    """
    Handle nested/escaped JSON in summary fields.
    Extract the actual structured data.
    """
    # Check if executive_summary contains nested JSON
    exec_sum = summary.get('executive_summary', '')
    raw_response = summary.get('raw_response', '')

    # Try to extract from raw_response first (it has the most complete data)
    json_source = raw_response if raw_response else exec_sum

    if isinstance(json_source, str) and '{' in json_source:
        # Try to extract values using regex
        exec_summary_val = extract_value_from_json_string(json_source, 'executive_summary')
        key_topics_val = extract_array_from_json_string(json_source, 'key_topics')
        action_items_val = extract_array_from_json_string(json_source, 'action_items')
        decisions_val = extract_array_from_json_string(json_source, 'decisions')
        discussion_points_val = extract_array_from_json_string(json_source, 'discussion_points')

        result = {
            'executive_summary': exec_summary_val if exec_summary_val else (exec_sum[:200] if exec_sum else ''),
            'key_topics': key_topics_val if key_topics_val else summary.get('key_topics', []),
            'decisions': decisions_val if decisions_val else summary.get('decisions', []),
            'action_items': action_items_val if action_items_val else summary.get('action_items', []),
            'discussion_points': discussion_points_val if discussion_points_val else summary.get('discussion_points', []),
            'next_meeting': summary.get('next_meeting'),
            # Preserve metadata
            'generated_at': summary.get('generated_at'),
            'provider': summary.get('provider'),
            'model': summary.get('model'),
            'language': summary.get('language'),
        }

        return result

    return summary


def generate_summary_markdown(summary):
    """Generate clean, copy-paste friendly markdown."""
    lines = []

    # Clean up nested JSON if present
    summary = parse_nested_summary(summary)

    # Header with metadata
    lines.append("╔════════════════════════════════════════════════════════════╗")
    lines.append("║                    📊 RINGKASAN RAPAT                       ║")
    lines.append("╚════════════════════════════════════════════════════════════╝")
    lines.append("")

    # Metadata
    generated_at = summary.get('generated_at', '')
    if generated_at:
        try:
            dt = datetime.fromisoformat(generated_at)
            lines.append(f"📅 {dt.strftime('%A, %d %B %Y - %H:%M WIB')}")
        except:
            lines.append(f"📅 {generated_at}")
    lines.append("")

    # Executive Summary
    lines.append("## Ringkasan Eksekutif")
    lines.append("─" * 60)
    exec_summary = summary.get('executive_summary', '')
    if exec_summary:
        # Clean up if it still has JSON artifacts
        exec_summary = str(exec_summary).replace('\\n', '\n').replace('\\"', '"')
        exec_summary = exec_summary[:500] if len(exec_summary) > 500 else exec_summary
        lines.append(exec_summary)
    else:
        lines.append("Tidak ada ringkasan eksekutif.")
    lines.append("")

    # Discussion Points (Hierarchical structure)
    discussion_points = summary.get('discussion_points', [])
    if discussion_points and isinstance(discussion_points, list):
        lines.append("## 🔍 Pembahasan Detail")
        lines.append("─" * 60)

        for topic_data in discussion_points:
            if isinstance(topic_data, dict):
                topic = topic_data.get('topic', 'Topik tanpa judul')
                ts_start = topic_data.get('timestamp_start', '')
                ts_end = topic_data.get('timestamp_end', '')

                # Topic header with timestamp
                if ts_start or ts_end:
                    lines.append(f"\n### 📌 {topic}")
                    if ts_start and ts_end:
                        lines.append(f"_{ts_start} - {ts_end}_")
                else:
                    lines.append(f"\n### 📌 {topic}")

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
                                lines.append(f"**• {point}**")
                                if details:
                                    lines.append(f"  {details}")
                                if speaker and speaker != 'null':
                                    lines.append(f"  _— {speaker}_")
                                lines.append("")

        lines.append("")

    # Key Topics (fallback if no discussion_points)
    elif summary.get('key_topics'):
        key_topics = summary.get('key_topics', [])
        lines.append("## 📌 Topik Utama")
        lines.append("─" * 60)
        for topic in key_topics:
            if topic and topic != "null":
                lines.append(f"• {topic}")
        lines.append("")
    decisions = summary.get('decisions', [])
    if decisions:
        lines.append("## ✅ Keputusan")
        lines.append("─" * 60)
        for i, decision in enumerate(decisions, 1):
            if isinstance(decision, dict):
                topic = decision.get('topic', f'Keputusan {i}')
                decision_text = decision.get('decision', '')
                by = decision.get('by', '')

                if decision_text:
                    if by:
                        lines.append(f"{i}. **{topic}**")
                        lines.append(f"   {decision_text}")
                        lines.append(f"   ├─ Oleh: {by}")
                    else:
                        lines.append(f"{i}. **{topic}**: {decision_text}")
                    lines.append("")

    # Action Items - THE MOST IMPORTANT PART FOR COPY-PASTE
    action_items = summary.get('action_items', [])
    if action_items:
        lines.append("## 📋 Daftar Tugas (Action Items)")
        lines.append("─" * 60)
        lines.append("")

        for i, item in enumerate(action_items, 1):
            if isinstance(item, dict):
                task = item.get('task', '')
                pic = item.get('pic', 'Belum ditentukan')
                deadline = item.get('deadline', '-')
                priority = item.get('priority', 'sedang').upper()

                if task:
                    lines.append(f"### {i}. {task}")
                    lines.append("")
                    lines.append(f"   ├─ 📌 PIC: {pic if pic and pic != 'null' else 'Belum ditentukan'}")
                    lines.append(f"   ├─ ⏰ Deadline: {deadline if deadline and deadline != 'null' else 'Tidak ditentukan'}")
                    lines.append(f"   └─ ⚡ Prioritas: {priority}")
                    lines.append("")

    # Next Meeting
    next_meeting = summary.get('next_meeting')
    if next_meeting and next_meeting != 'null':
        lines.append("## 📅 Rapat Berikutnya")
        lines.append("─" * 60)
        lines.append(next_meeting)
        lines.append("")

    # Footer
    lines.append("─" * 60)
    lines.append("")
    provider = summary.get('provider', 'unknown')
    model = summary.get('model', 'unknown')
    language = 'Bahasa Indonesia' if summary.get('language') == 'id' else 'English'
    lines.append(f"🤖 Dibuat oleh: {provider.upper()} ({model})")
    lines.append(f"🌐 Bahasa: {language}")
    lines.append("")
    lines.append("*Catatan: Ringkasan ini dibuat otomatis oleh AI.*")

    return "\n".join(lines)


def main():
    import sys

    # Get output base from command line or use default
    output_base = sys.argv[1] if len(sys.argv) > 1 else "transcript"

    summary_file = f"{output_base}_summary.json"

    if not os.path.exists(summary_file):
        print(f"❌ Error: {summary_file} not found")
        print("   Run summarization first with: ./process.sh <audio> --summarize")
        sys.exit(1)

    print(f"📖 Reading {summary_file}...")

    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    print(f"📝 Generating clean markdown...")
    markdown = generate_summary_markdown(summary)

    output_file = f"{output_base}_summary.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"✅ Summary saved to: {output_file}")
    print(f"   {len(markdown)} characters")
    print("")
    print("📋 Format: Clean, copy-paste friendly")
    print("   • Executive summary")
    print("   • Discussion points (with topics & sub-points)")
    print("   • Decisions made")
    print("   • Action items (with PIC, deadline, priority)")
    print("   • Next meeting info")


if __name__ == "__main__":
    main()

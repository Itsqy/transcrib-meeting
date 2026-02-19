#!/usr/bin/env python3
"""
Enhanced CLI for Indonesian Meeting Transcription System

Commands:
  transcribe       Transcribe audio with speaker diarization
  enroll-speaker   Enroll a new speaker for identification
  list-speakers    List all enrolled speakers
  rediarize        Re-run diarization on existing transcript
  summarize        Generate AI summary from transcript
  process-full     Run complete pipeline (transcribe + refine + format + summarize)
"""
import argparse
import sys
import json
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.transcriber import EnhancedTranscriber
from src.diarization import EnhancedDiarization
from src.speaker_id import SpeakerDatabase
from src.summarizer import MeetingSummarizer
from src.utils.config import get_config


def cmd_transcribe(args):
    """Transcribe audio with speaker diarization."""
    print(f"🚀 Transcribing: {args.audio}")
    print(f"   Model: {args.model}")
    print(f"   Device: {args.device}")
    print(f"   Speakers: {args.num_speakers or 'Auto-detect'}")
    print("")

    # Initialize transcriber
    config = get_config(args.config)
    if args.model:
        config.set('transcription', 'model', value=args.model)
    if args.device:
        config.set('transcription', 'device', value=args.device)

    transcriber = EnhancedTranscriber(args.config)

    # Transcribe with diarization
    num_speakers = int(args.num_speakers) if args.num_speakers else None
    segments, info = transcriber.transcribe_with_speakers(
        args.audio,
        num_speakers=num_speakers
    )

    # Format output
    diarization = EnhancedDiarization(args.config)
    diarized_segments = diarization.diarize(
        args.audio,
        num_speakers=num_speakers,
        segments=segments
    )

    # Write output
    output_file = args.output or "transcript_speakers.txt"
    write_transcript_with_speakers(diarized_segments, output_file)

    print("")
    print(f"✅ Transcription complete!")
    print(f"📄 Output: {output_file}")
    print(f"👥 Speakers detected: {len(set(s['speaker'] for s in diarized_segments))}")
    print(f"⏱️  Processing time: {info['processing_time']:.2f}s")


def cmd_enroll_speaker(args):
    """Enroll a new speaker."""
    print(f"🎤 Enrolling speaker: {args.name}")
    print(f"   Samples: {len(args.samples)}")
    print("")

    db = SpeakerDatabase(args.config)

    # Validate samples
    for sample in args.samples:
        if not Path(sample).exists():
            print(f"❌ Sample not found: {sample}")
            return 1

    # Enroll
    result = db.enroll(args.name, args.samples)

    if result['success']:
        print(f"✅ Successfully enrolled: {args.name}")
        print(f"   ID: {result['id']}")
        print(f"   Samples processed: {result['num_samples']}")
    else:
        print(f"❌ Enrollment failed: {result['error']}")
        return 1

    return 0


def cmd_list_speakers(args):
    """List all enrolled speakers."""
    db = SpeakerDatabase(args.config)
    speakers = db.list_speakers()

    if not speakers:
        print("No enrolled speakers found.")
        print("\nTo enroll a speaker:")
        print("  python scripts/cli.py enroll-speaker \"Name\" sample1.wav sample2.wav sample3.wav")
        return 0

    print(f"📋 Enrolled Speakers ({len(speakers)})")
    print("")

    for speaker in speakers:
        print(f"  🎤 {speaker['name']}")
        print(f"     ID: {speaker['id']}")
        print(f"     Samples: {speaker['num_samples']}")
        if speaker.get('metadata'):
            for key, value in speaker['metadata'].items():
                print(f"     {key}: {value}")
        print("")

    return 0


def cmd_rediarize(args):
    """Re-run diarization on existing transcript."""
    print(f"🔄 Re-diarizing: {args.transcript}")
    print(f"   Audio: {args.audio}")
    print(f"   Method: {args.method}")
    print("")

    # Load existing transcript
    if not Path(args.transcript).exists():
        print(f"❌ Transcript not found: {args.transcript}")
        return 1

    # Initialize diarization
    config = get_config(args.config)
    config.set('diarization', 'method', value=args.method)

    diarization = EnhancedDiarization(args.config)

    # Run diarization
    segments = parse_transcript(args.transcript)
    diarized_segments = diarization.diarize(
        args.audio,
        num_speakers=int(args.num_speakers) if args.num_speakers else None,
        segments=segments
    )

    # Write output
    output_file = args.output or "transcript_speakers_rediarized.txt"
    write_transcript_with_speakers(diarized_segments, output_file)

    print(f"✅ Re-diarization complete!")
    print(f"📄 Output: {output_file}")

    return 0


def cmd_summarize(args):
    """Generate AI summary from transcript."""
    print(f"🤖 Generating summary...")
    print(f"   Input: {args.transcript}")
    print(f"   Provider: {args.provider}")
    print("")

    # Load transcript
    if not Path(args.transcript).exists():
        print(f"❌ Transcript not found: {args.transcript}")
        return 1

    with open(args.transcript, 'r', encoding='utf-8') as f:
        transcript = f.read()

    # Initialize summarizer
    config = get_config(args.config)
    config.set('summarization', 'provider', value=args.provider)

    summarizer = MeetingSummarizer(args.config)

    # Generate summary
    summary = summarizer.summarize(transcript)

    # Write output
    output_file = args.output or "summary.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"✅ Summary generated!")
    print(f"📄 Output: {output_file}")

    # Print preview
    if summary.get('executive_summary'):
        print("\n📊 Executive Summary:")
        print(summary['executive_summary'][:200] + "...")

    return 0


def cmd_process_full(args):
    """Run complete pipeline."""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     Enhanced Indonesian Meeting Transcription System      ║")
    print "╚════════════════════════════════════════════════════════════╝"
    print("")

    # Check if audio exists
    if not Path(args.audio).exists():
        print(f"❌ Audio file not found: {args.audio}")
        return 1

    # Create args object for each step
    transcribe_args = argparse.Namespace(
        audio=args.audio,
        model=args.model,
        device=args.device,
        num_speakers=args.num_speakers,
        output="transcript_speakers.txt",
        config=args.config
    )

    # Step 1: Transcribe
    if cmd_transcribe(transcribe_args) != 0:
        return 1

    # Step 2: Refine (if not skipped)
    if not args.no_refine:
        print("\n🪄 Refining transcript...")
        os.system(f"python3 refine_transcript.py")

    # Step 3: Summarize (if requested)
    if args.summarize:
        print("\n🤖 Generating summary...")
        transcript_file = "transcript_speakers_refined.txt"
        if not Path(transcript_file).exists():
            transcript_file = "transcript_speakers.txt"

        summarize_args = argparse.Namespace(
            transcript=transcript_file,
            provider=args.provider,
            output="summary.json",
            config=args.config
        )

        if cmd_summarize(summarize_args) != 0:
            print("⚠️  Summarization failed, continuing...")

    # Step 4: Format
    print("\n🎨 Formatting output...")
    os.system(f"python3 format_md.py")

    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║                    ✅ ALL COMPLETE! ✅                     ║"
    print("╚════════════════════════════════════════════════════════════╝")

    return 0


def parse_transcript(filepath):
    """Parse transcript file into segments."""
    import re
    from src.utils.audio import parse_time

    segments = []
    current_speaker = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            speaker_match = re.match(r'^--- (.+?) ---$', line)
            if speaker_match:
                current_speaker = speaker_match.group(1)
                continue

            seg_match = re.match(r'\s*\[(\d+:\d+(?::\d+)?) - (\d+:\d+(?::\d+)?)\]\s*(.*)', line)
            if seg_match and current_speaker:
                start_str, end_str, text = seg_match.groups()
                segments.append({
                    'start': parse_time(start_str),
                    'end': parse_time(end_str),
                    'text': text.strip(),
                    'speaker': current_speaker
                })

    return segments


def write_transcript_with_speakers(segments, output_file):
    """Write transcript with speaker labels to file."""
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    lines = []
    prev_speaker = None

    for seg in segments:
        speaker = seg['speaker']
        timestamp = f"[{format_time(seg['start'])} - {format_time(seg['end'])}]"

        if speaker != prev_speaker:
            lines.append("")
            lines.append(f"--- {speaker} ---")
            prev_speaker = speaker

        lines.append(f"  {timestamp} {seg['text']}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines).strip())


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Indonesian Meeting Transcription System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--config', '-c', help='Path to config file')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # transcribe command
    transcribe_parser = subparsers.add_parser('transcribe', help='Transcribe audio with diarization')
    transcribe_parser.add_argument('audio', help='Audio file path')
    transcribe_parser.add_argument('--model', '-m', default='large-v3-turbo', help='Whisper model')
    transcribe_parser.add_argument('--device', '-d', choices=['auto', 'cpu', 'cuda', 'mps'], default='auto', help='Device')
    transcribe_parser.add_argument('--num-speakers', '-n', help='Number of speakers')
    transcribe_parser.add_argument('--output', '-o', help='Output file path')

    # enroll-speaker command
    enroll_parser = subparsers.add_parser('enroll-speaker', help='Enroll a new speaker')
    enroll_parser.add_argument('name', help='Speaker name')
    enroll_parser.add_argument('samples', nargs='+', help='Voice sample files (3-10 recommended)')

    # list-speakers command
    subparsers.add_parser('list-speakers', help='List enrolled speakers')

    # rediarize command
    rediarize_parser = subparsers.add_parser('rediarize', help='Re-run diarization')
    rediarize_parser.add_argument('audio', help='Audio file path')
    rediarize_parser.add_argument('--transcript', '-t', default='transcript_speakers.txt', help='Transcript file')
    rediarize_parser.add_argument('--method', '-m', choices=['pyannote', 'resemblyzer', 'hybrid'], default='hybrid', help='Diarization method')
    rediarize_parser.add_argument('--num-speakers', '-n', help='Number of speakers')
    rediarize_parser.add_argument('--output', '-o', help='Output file path')

    # summarize command
    summarize_parser = subparsers.add_parser('summarize', help='Generate AI summary')
    summarize_parser.add_argument('transcript', help='Transcript file path')
    summarize_parser.add_argument('--provider', '-p', choices=['openai', 'local'], default='openai', help='AI provider')
    summarize_parser.add_argument('--output', '-o', help='Output file path')

    # process-full command
    process_parser = subparsers.add_parser('process-full', help='Run complete pipeline')
    process_parser.add_argument('audio', help='Audio file path')
    process_parser.add_argument('--model', '-m', default='large-v3-turbo', help='Whisper model')
    process_parser.add_argument('--device', '-d', choices=['auto', 'cpu', 'cuda', 'mps'], default='auto', help='Device')
    process_parser.add_argument('--num-speakers', '-n', help='Number of speakers')
    process_parser.add_argument('--summarize', '-s', action='store_true', help='Generate AI summary')
    process_parser.add_argument('--provider', '-p', choices=['openai', 'local'], default='openai', help='AI provider')
    process_parser.add_argument('--no-refine', action='store_true', help='Skip text refinement')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch command
    commands = {
        'transcribe': cmd_transcribe,
        'enroll-speaker': cmd_enroll_speaker,
        'list-speakers': cmd_list_speakers,
        'rediarize': cmd_rediarize,
        'summarize': cmd_summarize,
        'process-full': cmd_process_full
    }

    command_func = commands.get(args.command)
    if command_func:
        return command_func(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())

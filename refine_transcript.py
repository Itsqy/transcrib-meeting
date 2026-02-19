"""
Refinement script for transcript improvement.
Fixes common Indonesian education terms (Kemendikbud context) and typos.
"""
import re
import os

# Dictionary of common misheard terms in Indonesian education context
GLOSSARY = {
    r"Fairfile": "Verval",
    r"Fair-file": "Verval",
    r"Fairfile": "Verval",
    r"Fairfile": "Verval",
    r"DAPODIC": "Dapodik",
    r"Dapodic": "Dapodik",
    r"Bintech": "Bimtek",
    r"Bintek": "Bimtek",
    r"Rombong": "Rombel",
    r"Samsaran": "Sasaran",
    r"Saksaran": "Sasaran",
    r"Pusatin": "Pusdatin",
    r"Dijen": "Ditjen",
    r"Vokassi": "Vokasi",
    r"IHP": "IFP",
    r"PID": "IFP", # Interactive Flat Panel often misheard as PID/IHP
    r"Saker": "Satker",
    r"BVJ": "PBJ",
    r"emas-emas": "mas-mas",
    r"ngedrift": "nge-draft",
    r"lola": "pengelola",
    r"digit pun": "digital",
    r"Sekrepinjang": "Sekretariat Ditjen",
    r"kontrapayu": "Kontrak Payung",
    r"hi-send": "Hisense",
    r"pinal": "final",
    r"apaham": "paham",
    r"akutabilitas": "akuntabilitas",
    r"teraksinya": "tracenya",
    r"komu": "kamu",
    r"merger": "merger",
    r"ABT": "ABT",
    r"perpang": "persiapan pengadaan",
}

def clean_text(text):
    """Apply glossary replacements and basic grammar fixes."""
    for pattern, replacement in GLOSSARY.items():
        # Match word with case-insensitivity but keep some logic
        compiled = re.compile(re.escape(pattern), re.IGNORECASE)
        text = compiled.sub(replacement, text)
    
    # Contextual cleanup (e.g., spaces after punctuation)
    text = re.sub(r'\s+([,.?!])', r'\1', text)
    
    # Fix common suffix issues
    text = text.replace("Dapodiknya", "Dapodik-nya")
    text = text.replace("Vervalnya", "Verval-nya")
    
    return text

def process_file(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"Refining {input_path}...")
    cleaned_content = clean_text(content)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_content)

    print(f"✓ Success! Refined version saved to: {output_path}")

if __name__ == "__main__":
    import sys

    # Get output base from command line or use default
    output_base = sys.argv[1] if len(sys.argv) > 1 else "transcript"

    # Refine raw text if exists
    input_file = f"{output_base}_speakers.txt"
    output_file = f"{output_base}_speakers_refined.txt"

    if os.path.exists(input_file):
        process_file(input_file, output_file)
    else:
        print(f"⚠️  Input file not found: {input_file}")

    # Refine markdown if exists
    md_input = f"{output_base}.md"
    md_output = f"{output_base}_refined.md"

    if os.path.exists(md_input):
        process_file(md_input, md_output)

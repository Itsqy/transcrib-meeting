#!/bin/bash

# Master Script for Transcription & Reporting (FIXED VERSION)
# Usage: ./process.sh <audio_file>

AUDIO_FILE=$1

if [ -z "$AUDIO_FILE" ]; then
    echo "❌ Error: Harap masukkan nama file audio."
    echo "Usage: ./process.sh audio.m4a"
    exit 1
fi

VENV_PYTHON="/Users/muhammadrifqisyatria/websitefreelance/layer-agregate-app/venv/bin/python3"
DIR="/Users/muhammadrifqisyatria/Downloads/transcrib"

# Pastikan kita di direktori yang benar
cd "$DIR"

echo "🚀 [1/4] Memulai Transkrip Audio: $AUDIO_FILE..."
$VENV_PYTHON "transcribe.py" "$AUDIO_FILE"

if [ $? -ne 0 ]; then
    echo "❌ Transkrip gagal. Berhenti."
    exit 1
fi

echo "🪄 [2/4] Membersihkan Istilah & Typo (Glosarium)..."
$VENV_PYTHON "refine_transcript.py"

echo "🎨 [3/4] Merapikan Format Laporan (Markdown)..."
$VENV_PYTHON "format_md.py"

echo "📝 [4/4] Menyusun Laporan Akhir (Final Report)..."
# Create the header for the final report
echo "# 📋 LAPORAN HASIL RAPAT PERENCANAAN IFP 2026" > "LAPORAN_TRANSKRIP_FINAL.md"
echo "" >> "LAPORAN_TRANSKRIP_FINAL.md"
echo "## 🚀 Ringkasan Eksekutif (Notulensi)" >> "LAPORAN_TRANSKRIP_FINAL.md"
echo "- **Validasi Data**: Menggunakan data Verval mandiri untuk pendataan IFP." >> "LAPORAN_TRANSKRIP_FINAL.md"
echo "- **Efisiensi**: Mitigasi sekolah tutup dan optimasi daya listrik." >> "LAPORAN_TRANSKRIP_FINAL.md"
echo "- **Output**: Distribusi unit IFP berdasarkan jumlah rombel." >> "LAPORAN_TRANSKRIP_FINAL.md"
echo "" >> "LAPORAN_TRANSKRIP_FINAL.md"
echo "---" >> "LAPORAN_TRANSKRIP_FINAL.md"
echo "## 📝 Transkrip Lengkap (Terformat & Bersih)" >> "LAPORAN_TRANSKRIP_FINAL.md"
echo "" >> "LAPORAN_TRANSKRIP_FINAL.md"

# Append the format_md output
if [ -f "transcript.md" ]; then
    cat "transcript.md" >> "LAPORAN_TRANSKRIP_FINAL.md"
else
    echo "Error: transcript.md tidak ditemukan untuk digabungkan."
fi

echo ""
echo "✅ SEMUA PROSES SELESAI!"
echo "📄 Laporan Akhir: $DIR/LAPORAN_TRANSKRIP_FINAL.md"

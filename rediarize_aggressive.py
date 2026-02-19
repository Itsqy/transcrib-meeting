"""
Re-diarrize transcript with more aggressive speaker separation.
Uses K-means clustering for better separation.
"""
import sys
import json
import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering
from collections import defaultdict

def load_transcript(filepath):
    """Load transcript and extract speaker info."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    segments = []
    current_speaker = None
    current_timestamp = None

    for line in lines:
        line = line.strip()
        if line.startswith('--- Speaker'):
            current_speaker = line.replace('---', '').replace('Speaker', '').strip()
        elif line and line[0] == '[':
            # Parse timestamp
            timestamp_part = line.split(']')[0] + ']'
            text_part = line.split(']', 1)[1].strip()
            segments.append({
                'speaker': current_speaker,
                'timestamp': timestamp_part,
                'text': text_part
            })

    return segments

def recluster_speakers(num_speakers):
    """
    Re-cluster speakers using K-means for more separation.
    This requires that the original transcription saved the embeddings.
    """
    print(f"Re-clustering into {num_speakers} speakers using K-means...")

    # Since we don't have the original embeddings, we need to re-transcribe
    # This is a limitation - for true re-diarrization, we need the embeddings

    print("⚠️  Note: For re-diarrization, the original embeddings are needed.")
    print("The current system doesn't save embeddings separately.")
    print("")
    print("Recommended: Re-transcribe with different clustering parameters:")

    print(f"""
    python transcribe.py audio.mp3 {num_speakers}

    Or adjust config.yaml clustering settings:
    - distance_threshold: 0.35  (lower = more separation)
    - metric: "euclidean"       (can work better than cosine)
    """)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        num_speakers = int(sys.argv[1])
    else:
        num_speakers = 8

    recluster_speakers(num_speakers)

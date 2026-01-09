# Audio Structure Analysis

Visualize the structure of hypnosis audio files using Self-Similarity Matrices (SSM).

## What It Does

SSM analysis reveals:
- **Repeated segments** - Loops, mantras, recurring content show as diagonal stripes
- **Unique sections** - Intros, outros, transitions appear as dark bands
- **Hidden modifications** - Sections that differ from expected patterns
- **Production differences** - EQ changes, binaural shifts, compression changes

## Quick Start

```bash
# Install dependencies
pip install librosa numpy matplotlib scipy openai

# Both acoustic + semantic analysis
export OPENAI_API_KEY="sk-..."
python ssm.py audio.mp3 --transcript audio.srt

# Acoustic only (no API key needed)
python ssm.py audio.mp3

# Semantic only
python ssm.py --transcript audio.srt
```

## Two Analysis Modes

### MFCC (Acoustic)

Analyzes **how the audio sounds** using Mel-frequency cepstral coefficients:
- Captures voice timbre, EQ, compression, binaural tones
- Shows production differences between sections
- No transcript required

```bash
python ssm.py audio.mp3 --hop-length 4096
```

### Text (Semantic)

Analyzes **what is being said** using OpenAI embeddings:
- Captures meaning regardless of audio production
- Robust to transcription errors
- Requires SRT transcript + API key

```bash
python ssm.py --transcript audio.srt --window-size 30 --hop-size 15
```

## Reading the Output

The SSM is a grid where each cell shows similarity between two time points:
- **Bright diagonal** = Main diagonal (self-comparison, always 1.0)
- **Parallel bright diagonals** = Repeated sections
- **Dark bands** = Unique content that doesn't repeat
- **Checkerboard patterns** = Alternating segment types (e.g., conditioning vs fractionation)

### Example: ABBBBC Structure

```
     A    B1   B2   B3   B4   C
A  [ ██   ░░   ░░   ░░   ░░   ░░ ]
B1 [ ░░   ██   ▓▓   ▓▓   ▓▓   ░░ ]
B2 [ ░░   ▓▓   ██   ▓▓   ▓▓   ░░ ]
B3 [ ░░   ▓▓   ▓▓   ██   ▓▓   ░░ ]
B4 [ ░░   ▓▓   ▓▓   ▓▓   ██   ░░ ]
C  [ ░░   ░░   ░░   ░░   ░░   ██ ]

██ = self (1.0)    ▓▓ = similar (0.8+)    ░░ = different (0.3-)
```

## Use Cases

### Verify Loop Structure
Confirm your intended ABBBBC pattern actually appears in the final audio.

### Detect Hidden Content
Compare SSMs of unknown files - anomalies in the pattern may indicate modifications.

### Subliminal Detection
Text SSM can accidentally detect subliminals when they're loud enough to confuse the transcription.

### Production Consistency
MFCC SSM shows if EQ/compression varies between sections (intentional or not).

## Options

```
--output-dir, -o    Output directory (default: current)
--name, -n          Base name for output files
--hop-length        MFCC resolution (default: 4096, larger=faster)
--sample-rate       Audio sample rate (default: 22050)
--window-size       Text chunk window in seconds (default: 30)
--hop-size          Text chunk hop in seconds (default: 15)
--embedding-model   OpenAI model (default: text-embedding-3-small)
```

## Output Files

For input `session.mp3`:
- `session_mfcc_ssm.png` - Acoustic similarity visualization
- `session_mfcc_ssm.npz` - Raw numpy data
- `session_text_ssm.png` - Semantic similarity visualization
- `session_text_ssm.npz` - Raw numpy data

## Technical Notes

### MFCC Explained
MFCCs are 13 coefficients capturing the "spectral shape" of audio:
- MFCC 0: Overall energy
- MFCC 1: Spectral tilt (bassy vs trebly)
- MFCC 2: Spectral curvature (scooped vs mid-heavy)
- Higher coefficients: Finer spectral detail

They're computed per frame (~93ms windows), normalized, then compared via cosine similarity.

### Text Embeddings
30-second overlapping windows of transcript text are embedded using OpenAI's text-embedding-3-small (1536 dimensions). Cosine similarity between embeddings shows semantic relatedness regardless of exact wording.

### Memory Usage
A 60-minute file at hop_length=4096 produces ~40k frames = ~6GB SSM matrix. Use hop_length=8192 or higher for longer files.

## License

MIT

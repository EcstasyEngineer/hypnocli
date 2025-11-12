# Hypnocli — GIF maker for hypnotic loops

## Safety Warning
⚠️ This tool can produce high-contrast flicker. Use responsibly. See WCAG SC 2.3.1 and consider keeping risk moderate when sharing output.

## What it does
Builds animated GIFs from folders of images with:
- Optional text overlays with various styles
- Color cycling backgrounds
- Randomized or static image/text placement
- Full reproducibility via metadata

---

## Quick Start

### Basic GIF
```bash
python3 gifmaker.py --input-dir input/myimages --colors "#000|#fff" --frames 20 --output outputs/basic.gif
```

### With Sequential Text
```bash
python3 gifmaker.py --input-dir input/myimages --text input/mytext.txt --text-color INVERSE --outline stroke --colors "#FF008E|#00FF71" --output outputs/text.gif
```

### With Random/Sparse Text
```bash
python3 gifmaker.py --input-dir input/myimages --frames 50 --shuffle-text --text-density 0.4 --text input/mytext.txt --colors "#FF008E|#00FF71" --output outputs/sparse.gif
```

### With Static Image Mapping
```bash
python3 gifmaker.py --input-dir input/myimages --image-map input/my_image_map.txt --text input/mytext.txt --colors "#FF008E|#00FF71" --output outputs/static.gif
```

---

## Core Concepts

### Images
- **Default behavior**: Images are placed **randomly** across frames (controlled by `--seed`)
- **Static mapping**: Use `--image-map` to specify exactly which image appears on each frame
- **Frame count**: Derived from text line count, image count, or explicit `--frames`

### Text
- **Default behavior**: Text maps **sequentially** (line 1 → frame 1, line 2 → frame 2, etc.)
- **Random mode**: Use `--shuffle-text` to randomize text order and placement
- **Sparse text**: Combine `--shuffle-text` with `--text-density` (0.0-1.0) for partial text coverage
- **Special markers**:
  - Lines with `*` render at 50% opacity (e.g., `TOY*`)
  - Lines with just `-` render as empty frames

### Colors
- Background colors cycle through frames
- **Continuous mode** (default): Color advances every frame
- **Interrupt mode** (`--inter`): Color advances only on color-only frames (no image)
- **Tip**: For smooth loops, use frame counts that are multiples of color count

---

## Common Options

### Timing Presets
- `--crawl`: 6.25 fps (160 ms) - theta waves
- `--slow`: 10.0 fps (100 ms) - low alpha
- `--medium`: 12.5 fps (80 ms) - alpha waves (default)
- `--fast`: 16.67 fps (60 ms) - low beta
- `--hyper`: 20.0 fps (50 ms) - beta waves
- Custom: `--ms 500` or `--fps 2.0`

### Aspect Ratios
- `--aspect square`: 1000×1000 (default)
- `--aspect wide`: 1280×720
- `--aspect tall`: 720×1280
- Custom: `--width 800 --height 600`

### Text Styling
- `--text-color INVERSE`: Inverts pixels under text (recommended)
- `--text-color "#FFFFFF"`: Solid color
- `--outline stroke`: Crisp outline (default)
- `--outline shadow`: Soft shadow
- `--outline none`: No outline
- `--text-scale 0.6`: Width fraction for text (0.0-1.0)

### Colors
- Single: `--colors "#FF0000"`
- Multiple: `--colors "#FF008E|#00FF71|#BA33B1|#2AFF4E"`
- Named: `--colors "red|blue|green"`

---

## Advanced Features

### Shuffle Text Options

**Random text order (all frames get text):**
```bash
python3 gifmaker.py --input-dir input/images --frames 30 --shuffle-text --text input/words.txt --output outputs/shuffled.gif
```

**Sparse random text (only 20% of frames have text):**
```bash
python3 gifmaker.py --input-dir input/images --frames 50 --shuffle-text --text-density 0.2 --text input/words.txt --output outputs/sparse.gif
```

**Why use shuffle-text?**
- Prevents semantic satiation (words losing meaning from repetition)
- Creates unpredictable patterns
- Allows sparse subliminal messaging

### Image Mapping

Create an `image_map.txt` file with one line per frame:
```
image1.png
-
image2.png
image2.png
-
image3.png
```
- Filename = use that image
- `-` = color-only frame (no image)

Then use:
```bash
python3 gifmaker.py --input-dir input/images --image-map input/image_map.txt --output outputs/mapped.gif
```

### Reproducibility & Extraction

All GIFs include metadata for full reproducibility.

**Extract the exact command used to create a GIF:**
```bash
python3 gifmaker.py --extract-opts outputs/mygif.gif
```

**Extract image mapping:**
```bash
python3 gifmaker.py --extract-images outputs/mygif.gif > extracted_images.txt
```

**Extract text mapping:**
```bash
python3 gifmaker.py --extract-text outputs/mygif.gif > extracted_text.txt
```

**Reproduce with extracted mappings:**
```bash
python3 gifmaker.py --image-map extracted_images.txt --text extracted_text.txt --colors "#FF008E|#00FF71" --output reproduced.gif
```

**Why extract?**
- Preserve exact frame sequence even if source files change
- Fork/modify existing GIFs
- Convert random generations to static mappings

---

## Image Fitting

Images are automatically fitted to the output dimensions:

- `--fit auto` (default): Mirror-pad to fill canvas
- `--fit crop`: Scale and center-crop to cover
- `--fit stretch`: Stretch to dimensions (may distort)

Add tint overlay:
```bash
--opacity 15        # 15% tint on all colors
--opacity "10|20|15"  # Per-color tint percentages
```

---

## Examples

### House Palette Loop
```bash
python3 gifmaker.py \
  --input-dir input/myimages \
  --text input/mantras.txt \
  --colors "#FF008E|#00FF71|#BA33B1|#2AFF4E" \
  --aspect wide \
  --medium \
  --text-color INVERSE \
  --outline stroke \
  --output outputs/hypno.gif
```

### Sparse Subliminals
```bash
python3 gifmaker.py \
  --input-dir input/photos \
  --frames 100 \
  --shuffle-text \
  --text-density 0.15 \
  --text input/subliminals.txt \
  --ms 500 \
  --colors "#000000" \
  --text-color "#FFFFFF" \
  --output outputs/subliminal.gif
```

### Static Sequence from Photoshop Project
```bash
# Extract from reference GIF
python3 gifmaker.py --extract-images reference.gif > my_sequence.txt
python3 gifmaker.py --extract-text reference.gif > my_text.txt

# Regenerate with modifications
python3 gifmaker.py \
  --input-dir input/newimages \
  --image-map my_sequence.txt \
  --text my_text.txt \
  --colors "#FF0000|#00FF00" \
  --output outputs/modified.gif
```

---

## Tips

- **Frame count**: For smooth color loops, use multiples of your color count (e.g., 20 frames with 4 colors)
- **Text line count**: In sequential mode (no `--shuffle-text`), frame count defaults to text line count
- **Reproducibility**: Use `--seed` to get the same random placement every time
- **Asterisk opacity**: Add `*` to any text line for 50% opacity (e.g., `OBEY*`)
- **Performance**: Larger images and more frames = longer processing time

---

## License
MIT - see `LICENSE`

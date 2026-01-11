# Hypnocli

CLI tools for hypnosis content generation, script composition, and audio rendering.

## Packages

### script/
Content generation tools using LLM.

- **`phase_chat_generator.py`** - Production script generator using TidalCycles-inspired phase structure
- **`generate_mantras.py`** - LLM-powered mantra generation with template variables

```bash
# Generate a full hypnosis script
python script/phase_chat_generator.py \
  --theme "relaxation + focus training" \
  --style "Permissive" \
  --tone "gentle, warm, confident" \
  --duration "10 minutes" \
  --out_dir out_session

# Generate mantras for a theme
python script/generate_mantras.py \
  --theme obedience \
  --count 20 \
  --difficulty LIGHT,MODERATE \
  --output mantras.json
```

Pre-built loop scripts available in `script/loops/`.

### tts/
AWS Polly integration for text-to-speech rendering.

- **`render_polly.py`** - Render text files to MP3 with automatic chunking

```bash
# Render a script to audio
python tts/render_polly.py script.txt output.mp3 --voice salli --engine neural

# Batch render a directory
python tts/render_polly.py scripts/ audio/ --batch
```

### gifmaker/
GIF maker for hypnotic visual loops. See [gifmaker/README.md](gifmaker/README.md).

### analysis/
Analysis tools for content and state modeling.

## Environment Setup

Create a `.env` file in the repo root:

```env
# LLM Provider (for script/mantra generation)
LLM_API_KEY=your_api_key
LLM_BASE_URL=xai          # or: openai, openrouter, ollama, lmstudio
LLM_MODEL=grok-4-0414     # optional, uses provider default

# AWS (for TTS rendering)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
```

Supported LLM providers:
- `openai` - OpenAI API
- `xai` / `grok` - xAI/Grok API
- `openrouter` - OpenRouter
- `ollama` - Local Ollama
- `lmstudio` - Local LM Studio

## Related Repos

- **[autotranceweb](https://github.com/EcstasyEngineer/autotranceweb)** - Theme taxonomy/ontologies, web UI, session playback
- **[conditioner](https://github.com/EcstasyEngineer/conditioner)** - Discord bot that consumes generated content

## License

MIT. See `LICENSE`.

Hypnocli Monorepo

- Packages
  - [gifmaker/](gifmaker/) — GIF maker for hypnotic loops (CLI). See [gifmaker/README.md](gifmaker/README.md) for usage, safety notes, and examples.
  - [pollytools/](pollytools/) — Script processing + AWS Polly integration (scoping in progress).

Quick start
- `cd gifmaker`
- Minimal: `python3 gifmaker.py --input-dir examples --colors "#000|#fff" --frames 8 --output outputs/minimal.gif`
- Text: `python3 gifmaker.py --input-dir examples --medium --text examples/text.txt --text-color INVERSE --output outputs/text_inverse.gif`
- Frame map: `python3 gifmaker.py --input-dir examples --frame-map examples/frame_map.txt --colors "#ff008e|#00ff71|#ba33b1|#2aff4e" --output outputs/mapped.gif`

License
- MIT. See `LICENSE`.

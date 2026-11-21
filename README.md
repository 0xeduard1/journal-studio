# journal-studio

The tiny open-source video studio behind the **0xeduard1** learning journal: short vertical clips that explain, simply, what I learn on my way from zero to smart contract auditor.

A clip is a JSON script. `make.py` turns it into a 1080×1920 MP4 with voice and captions:

```bash
pip install kokoro-onnx soundfile playwright
python3 -m playwright install chromium   # plus ffmpeg on your PATH
python3 make.py scripts/001-binary.json out/001-binary.mp4
```

- **Voice:** [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) (open-source TTS, runs on CPU; models download on first run)
- **Frames:** `render.html`, drawn by headless Chromium through Playwright
- **Video:** ffmpeg

## Script format

```json
{"id":"001-binary","series":"CS50x Week 0","caption":"post text…",
 "scenes":[{"type":"title","tag":"DAY 2","h":"Computers only know *two* numbers.","say":"…"}]}
```

Scene types: `title`, `explain` (`lines`), `code` (`code`, `hl`), `list` (`items`: `[icon, text]`), `big` (`big`, `sub`), `outro`.
`*word*` is highlighted on screen and in the captions. `say` is what the voice reads.

Follow the journey: [x.com/0xeduard1](https://x.com/0xeduard1)

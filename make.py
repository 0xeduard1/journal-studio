#!/usr/bin/env python3
"""0xeduard1 studio: turns a clip script (JSON) into a vertical 1080x1920 MP4 with voice and captions.

Usage: python3 make.py scripts/clip.json out/clip.mp4 [--voice am_michael] [--fps 30]
Open source only: Kokoro TTS (kokoro-onnx), Playwright/Chromium, ffmpeg.
"""
import argparse, asyncio, json, os, re, shutil, subprocess, sys, tempfile, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
MODELS = HERE / "models"
URLS = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
SR = 24000


def ensure_models():
    MODELS.mkdir(exist_ok=True)
    for name, url in URLS.items():
        p = MODELS / name
        if not p.exists() or p.stat().st_size < 1_000_000:
            print("downloading", name, file=sys.stderr)
            urllib.request.urlretrieve(url, p)


def plain(s):  # text for the voice: drop *emphasis* marks
    return re.sub(r"\*(.+?)\*", r"\1", s)


def caption_chunks(say, words_per=4):
    toks = say.split()
    chunks, cur = [], []
    for w in toks:
        cur.append(w)
        if len(cur) >= words_per or re.search(r"[.!?,:;]$", w.strip("*")):
            chunks.append(" ".join(cur)); cur = []
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def cap_html(chunk):
    c = chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*(.+?)\*", r"<b>\1</b>", c)


def tts(scenes, voice, speed):
    import numpy as np, soundfile as sf
    from kokoro_onnx import Kokoro
    k = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    pad = np.zeros(int(SR * 0.45), dtype="float32")
    track, timeline, t0 = [], [], 0.0
    for sc in scenes:
        audio, sr = k.create(plain(sc["say"]), voice=voice, speed=speed, lang="en-us")
        audio = audio.astype("float32")
        speak = len(audio) / sr
        dur = max(speak + 0.45, float(sc.get("min", 2.5)))
        seg = np.concatenate([audio, np.zeros(int(SR * (dur - speak)), dtype="float32")])
        chunks = caption_chunks(sc["say"])
        total = sum(len(plain(c)) for c in chunks) or 1
        caps, ct = [], 0.0
        for c in chunks:
            d = speak * len(plain(c)) / total
            caps.append((ct, ct + d, cap_html(c))); ct += d
        timeline.append({"start": t0, "dur": dur, "caps": caps})
        track.append(seg); t0 += dur
    wav = np.concatenate(track + [pad])
    return wav, timeline, t0 + len(pad) / SR


async def frames(script, timeline, total, fps, outdir):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        await pg.goto((HERE / "render.html").as_uri())
        await pg.wait_for_timeout(1500)
        n = int(total * fps)
        for f in range(n):
            T = f / fps
            i = next((j for j, tl in enumerate(timeline) if T < tl["start"] + tl["dur"]), len(timeline) - 1)
            tl, sc = timeline[i], script["scenes"][i]
            t = T - tl["start"]
            cap = next((c for a, z, c in tl["caps"] if a <= t < z + 0.15), "")
            await pg.evaluate("s=>draw(s)", {"sc": sc, "t": t, "dur": tl["dur"], "cap": cap, "T": T,
                                             "Ttot": total, "series": script.get("series", "")})
            await pg.screenshot(path=f"{outdir}/{f:05d}.jpg", type="jpeg", quality=90)
        await b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("out")
    ap.add_argument("--voice", default="am_michael"); ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--music", type=float, default=0.10, help="music volume under the voice (0 = no music)")
    a = ap.parse_args()
    script = json.loads(Path(a.script).read_text())
    ensure_models()
    import soundfile as sf
    wav, timeline, total = tts(script["scenes"], a.voice, a.speed)
    tmp = Path(tempfile.mkdtemp())
    if a.music > 0:
        from music import track
        import numpy as np
        m = track(len(wav) / SR + 0.1, seed=len(script["scenes"]))
        m = np.pad(m, (0, max(0, len(wav) - len(m))))[:len(wav)]
        wav = wav + a.music * m
        wav = wav / max(1.0, float(abs(wav).max()) / 0.98)
    sf.write(tmp / "voice.wav", wav, SR)
    asyncio.run(frames(script, timeline, total, a.fps, tmp))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", f"{tmp}/%05d.jpg",
                    "-i", str(tmp / "voice.wav"), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", "-movflags", "+faststart", a.out],
                   check=True)
    shutil.rmtree(tmp)
    print(f"{a.out}  {total:.1f}s")


if __name__ == "__main__":
    main()

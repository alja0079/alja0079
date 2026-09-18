# Bushra lip-sync toolkit

Animates Bushra's still image with SadTalker, driven by her own voice from
`bushra_ep1.mp4`, and splices the result back over her three on-screen scenes.
Every other scene, the original audio, and the original timing are left alone.

> **Why you run this yourself:** the Claude session that wrote this ran in a
> cloud Linux container with no GPU and no access to `C:\Users\K\Downloads`.
> These scripts are the pipeline; your machine has the GPU and the files.

---

## What it does

1. **analyze** – probes the video, detects scene cuts, transcribes the audio to
   find where you say *"Now the key step"*, checks which scenes show a face, and
   writes a `config.json` with three proposed segments.
2. **clips** – cuts the audio for each segment and renders a talking-head clip
   from the still image with SadTalker (mouth, head pose, and natural blinking).
3. **assemble** – overlays those clips onto the original video **only inside
   their time windows**.

The original audio stream is copied through **bit-for-bit**, and the generated
frames are overlaid onto the original timeline rather than re-cut into it. Total
duration and every caption cue therefore land exactly where they did before.

Verified on a synthetic test episode: untouched frames come out pixel-identical
to the source, audio MD5 is unchanged, and the output duration matches the input
to the millisecond.

---

## Requirements

| | |
|---|---|
| GPU | NVIDIA, 6 GB VRAM or more (CPU works but is ~20x slower) |
| Python | 3.10 recommended (3.11 fine; 3.12+ is rough on these deps) |
| ffmpeg | on `PATH` — `winget install --id Gyan.FFmpeg -e` |
| git | `winget install --id Git.Git -e` |
| Disk | ~8 GB (PyTorch + checkpoints) |

After installing ffmpeg, **open a new terminal** so `PATH` refreshes.

---

## 1. Install

From the folder containing these scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_sadtalker.ps1
```

This creates a venv, installs a CUDA PyTorch build matched to your GPU, clones
SadTalker, downloads ~2 GB of checkpoints, and applies three required
compatibility patches (see *Patches* below). Re-running is safe — downloads
resume and patches are idempotent.

It prints the venv python path at the end. Call it `$PY`:

```powershell
$PY = "$env:USERPROFILE\ai\SadTalker\.venv\Scripts\python.exe"
$ST = "$env:USERPROFILE\ai\SadTalker"
$PROJ = "C:\Users\K\Downloads\Bushra Episode 1"
```

Use that python for every stage — the system one has no torch.

## 2. Analyze, then **check the segment times**

```powershell
& $PY pipeline.py analyze `
    --project-dir $PROJ `
    --video bushra_ep1.mp4 `
    --image "ChatGPT_Image_Sep_18__2026__01_28_13_PM.png" `
    --sadtalker-dir $ST
```

It prints every scene with timestamps, flags which ones contain a face, marks
the scene holding *"Now the key step"*, and drops thumbnails in
`_lipsync_work\thumbs\`.

**This is the one step that needs your eyes.** Automatic scene detection is a
good guess, not gospel. Open `config.json`, compare against the thumbnails, and
fix the three `start`/`end` values:

```json
"segments": [
  { "name": "intro",    "start": 0.0,   "end": 12.4,  "enabled": true },
  { "name": "key_step", "start": 96.2,  "end": 118.0, "enabled": true },
  { "name": "outro",    "start": 205.5, "end": 219.9, "enabled": true }
]
```

If it found fewer than three, it says so — fill in the rest by hand.
Too few or too many scenes detected? Re-run with
`--scene-threshold 0.20` (more cuts) or `0.45` (fewer).
For a more accurate phrase match: `--whisper-model medium`.

## 3. Render and assemble

```powershell
& $PY pipeline.py all --config "$PROJ\config.json"
```

Or one stage at a time (`clips`, then `assemble`). Rendering is the slow part —
roughly 1–3 minutes of GPU time per minute of speech at `size: 256` with GFPGAN.

**Check a short preview before committing to a full encode:**

```powershell
& $PY pipeline.py assemble --config "$PROJ\config.json" --preview
```

That writes `bushra_ep1_talking_PREVIEW.mp4` — ~15 s around the first segment.

Result: **`bushra_ep1_talking.mp4`**, next to the original.

---

## Captions

How to handle captions depends on how they're in the file:

- **Burned into the picture** — full-frame replacement would erase them inside
  the three windows. Set `caption_band` to the rectangle they occupy and the
  original band is composited back on top of the generated frames:

  ```json
  "caption_band": { "y": 900, "h": 180 }
  ```

  `y` is pixels from the top, `h` the band height, in source resolution.
  Read them off a thumbnail in any image editor. Leave it `null` if captions
  never overlap Bushra's scenes.

- **A separate subtitle track** — nothing to do. Subtitle streams are mapped
  through automatically.

- **Added later in your editor** — nothing to do; timing is unchanged.

---

## Tuning

Everything below lives in `config.json`.

| Key | Effect |
|---|---|
| `sadtalker.preprocess` | `full` keeps her whole framing (default). `crop` outputs a tight face box. `extfull` is a wider full. |
| `sadtalker.size` | `256` (default) or `512` — sharper, slower, more VRAM. |
| `sadtalker.still` | `false` (default) gives head motion. `true` locks the head — steadier, less alive. |
| `sadtalker.expression_scale` | `1.0` default. `1.2–1.4` for more expressive; over ~1.6 goes rubbery. |
| `sadtalker.pose_style` | `0`–`45`, different head-motion patterns. |
| `sadtalker.enhancer` | `"gfpgan"` for face restoration, `null` to skip (faster). |
| `sadtalker.batch_size` | Lower to `1` if you hit CUDA OOM. |
| `fit` | `cover` (fill, crop overflow), `contain` (letterbox), `stretch`. |
| `encode.encoder` | `libx264` (default) or `h264_nvenc` for a fast GPU encode. |
| `segments[].enabled` | `false` to skip one segment without deleting it. |

Set `"cpu": true` under `sadtalker` to force CPU rendering.

---

## Troubleshooting

**`torch.cuda.is_available()` is False** — the NVIDIA driver is older than the
CUDA build. Update the driver; no reinstall needed.

**CUDA out of memory** — set `"batch_size": 1`, `"size": 256`, and
`"enhancer": null`.

**The face isn't detected in the still image** — SadTalker needs one clear,
roughly front-facing face. Crop the PNG closer to her head and shoulders and
re-run `clips --force`.

**Output duration drifted** — the pipeline warns if it does. It means a segment
extends past the end of the video; check the last segment's `end`.

**Re-render after changing settings** — `clips` skips clips that already exist.
Use `--force` to redo them.

**The seam at the scene boundary is visible** — `preprocess: "full"` pastes the
animated face back into the still. If the still doesn't match the original shot's
framing, nudge `fit`, or crop the PNG to match her on-screen framing.

---

## Patches applied at install

SadTalker's last release predates three breaking dependency changes.
`patch_sadtalker.py` fixes all three, idempotently:

1. torchvision ≥ 0.17 removed `torchvision.transforms.functional_tensor`, which
   `basicsr` imports at module level → rewritten to `torchvision.transforms.functional`.
2. librosa ≥ 0.10 made `librosa.filters.mel()` keyword-only → SadTalker's
   positional call in `src/utils/audio.py` is rewritten.
3. torch ≥ 2.6 defaults `torch.load(weights_only=True)`, which rejects
   SadTalker's `.pth.tar` checkpoints → a shim at the top of `inference.py`
   restores the old default.

---

## Why SadTalker and not LivePortrait

LivePortrait is **video-driven**: it transfers expression from a driving *video*
onto a still. It has no audio path, so it can't lip-sync to a voice track on its
own — you'd have to film or source a driving performance first.

SadTalker is **audio-driven**: still image + audio → video, with head pose and
blinking generated from the speech. That's exactly this job, so it's the default
here. If you later want finer control over the performance, LivePortrait is a
good second pass on SadTalker's output.

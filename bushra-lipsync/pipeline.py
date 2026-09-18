#!/usr/bin/env python3
"""
Replace Bushra's on-screen scenes in bushra_ep1.mp4 with an audio-driven
talking-head animation of her still image, leaving every other scene,
the original audio, and the original timing untouched.

Stages
  analyze   probe the video, cut-detect, transcribe, locate "Now the key step",
            and write config.json with three proposed segments
  clips     slice the audio per segment and render each one through SadTalker
  assemble  overlay the rendered clips back onto the original timeline

Run `analyze`, eyeball/edit config.json, then `clips` and `assemble`
(or `all` to chain clips+assemble once the segments are confirmed).

The original audio stream is copied through untouched, so lip timing can
never drift relative to the rest of the episode.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

KEY_PHRASE = "now the key step"


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def die(msg):
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def need(tool):
    if shutil.which(tool) is None:
        die(f"'{tool}' not found on PATH. Install ffmpeg and reopen your terminal.")
    return tool


def run(cmd, cwd=None, capture=False, check=True, quiet=False):
    printable = " ".join(str(c) for c in cmd)
    if not quiet:
        print(f"  $ {printable[:400]}{'...' if len(printable) > 400 else ''}")
    r = subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd) if cwd else None,
        capture_output=capture,
        text=True,
    )
    if check and r.returncode != 0:
        if capture:
            sys.stderr.write((r.stdout or "")[-4000:])
            sys.stderr.write((r.stderr or "")[-4000:])
        die(f"command failed (exit {r.returncode}): {printable[:300]}")
    return r


def fmt_ts(t):
    t = max(0.0, float(t))
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):d}:{int(m):02d}:{s:06.3f}"


def parse_rate(text):
    """'30000/1001' -> 29.97"""
    if not text:
        return 0.0
    if "/" in text:
        num, den = text.split("/", 1)
        try:
            den = float(den)
            return float(num) / den if den else 0.0
        except ValueError:
            return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def probe(video: Path):
    need("ffprobe")
    r = run(["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(video)],
            capture=True, quiet=True)
    data = json.loads(r.stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        die(f"no video stream in {video}")
    a = [s for s in data["streams"] if s["codec_type"] == "audio"]
    subs = [s for s in data["streams"] if s["codec_type"] == "subtitle"]

    fps = parse_rate(v.get("avg_frame_rate")) or parse_rate(v.get("r_frame_rate")) or 25.0
    duration = float(data["format"].get("duration") or v.get("duration") or 0.0)

    # Rotation metadata means displayed W/H are swapped.
    rotation = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            try:
                rotation = int(abs(float(sd["rotation"]))) % 360
            except (TypeError, ValueError):
                pass
    w, h = int(v["width"]), int(v["height"])
    if rotation in (90, 270):
        w, h = h, w

    return {
        "width": w, "height": h, "fps": round(fps, 6),
        "duration": duration,
        "has_audio": bool(a),
        "n_subtitle_streams": len(subs),
        "video_codec": v.get("codec_name"),
    }


# --------------------------------------------------------------------------
# analyze
# --------------------------------------------------------------------------
def detect_scenes(video: Path, threshold: float, duration: float):
    """Return scene-cut timestamps using ffmpeg's scene score."""
    need("ffmpeg")
    print(f"  scene detection (threshold {threshold}) ...")
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
             "-filter:v", f"select='gt(scene,{threshold})',showinfo",
             "-an", "-f", "null", "-"],
            capture=True, check=False, quiet=True)
    cuts = sorted({round(float(m), 3)
                   for m in re.findall(r"pts_time:([0-9]+\.?[0-9]*)", r.stderr or "")})
    cuts = [c for c in cuts if 0.05 < c < duration - 0.05]
    print(f"  found {len(cuts)} cuts")
    return cuts


def scenes_from_cuts(cuts, duration):
    bounds = [0.0] + list(cuts) + [round(duration, 3)]
    out = []
    for a, b in zip(bounds, bounds[1:]):
        if b - a >= 0.4:          # ignore sub-half-second flashes
            out.append((round(a, 3), round(b, 3)))
    return out


def transcribe(video: Path, model_size: str):
    """Word-level transcript via faster-whisper. Returns [] if unavailable."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("  faster-whisper not installed - skipping transcription.")
        print("  (pip install faster-whisper  to auto-locate the 'Now the key step' scene)")
        return []

    device, compute = "cuda", "float16"
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute)
    except Exception as e:
        print(f"  CUDA whisper unavailable ({type(e).__name__}) - falling back to CPU")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"  transcribing with whisper '{model_size}' ...")
    segments, _info = model.transcribe(str(video), word_timestamps=True, vad_filter=True)
    words = []
    for seg in segments:
        for w in (seg.words or []):
            token = re.sub(r"[^a-z0-9' ]", "", w.word.lower()).strip()
            if token:
                words.append({"w": token, "start": float(w.start), "end": float(w.end)})
    print(f"  transcribed {len(words)} words")
    return words


def find_phrase(words, phrase):
    """Best fuzzy match of `phrase` over a sliding word window."""
    target = phrase.lower().split()
    if not words or not target:
        return None
    n = len(target)
    best, best_score = None, 0.0
    for i in range(len(words) - n + 1):
        window = words[i:i + n]
        text = " ".join(x["w"] for x in window)
        score = SequenceMatcher(None, text, " ".join(target)).ratio()
        if score > best_score:
            best_score, best = score, (window[0]["start"], window[-1]["end"], text)
    if best and best_score >= 0.70:
        return {"start": best[0], "end": best[1], "matched": best[2], "score": round(best_score, 3)}
    return None


def has_face(video: Path, t0, t1, samples=5):
    """Sample a few frames in [t0,t1] and report whether a face is visible."""
    try:
        import cv2
    except ImportError:
        return None
    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        return None
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    hits = 0
    try:
        span = max(t1 - t0, 0.1)
        for k in range(samples):
            t = t0 + span * (k + 0.5) / samples
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            scale = 640.0 / max(frame.shape[1], 1)
            if scale < 1.0:
                frame = cv2.resize(frame, None, fx=scale, fy=scale)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                             minSize=(40, 40))
            if len(faces):
                hits += 1
    finally:
        cap.release()
    return hits >= max(1, samples // 3)


def save_thumbnails(video: Path, scenes, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    for i, (a, b) in enumerate(scenes):
        mid = a + (b - a) / 2.0
        dest = outdir / f"scene_{i:02d}_{a:07.2f}s.jpg"
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{mid:.3f}",
             "-i", str(video), "-frames:v", "1", "-vf", "scale=480:-2", str(dest)],
            check=False, quiet=True)
    print(f"  thumbnails -> {outdir}")


def cmd_analyze(args):
    proj = Path(args.project_dir).resolve()
    video = proj / args.video
    image = proj / args.image
    if not video.is_file():
        die(f"video not found: {video}")
    if not image.is_file():
        matches = sorted(proj.glob("*.png")) + sorted(proj.glob("*.jpg"))
        hint = "\n  ".join(str(m.name) for m in matches[:10])
        die(f"image not found: {image}\nImages in that folder:\n  {hint or '(none)'}")

    print(f"Project : {proj}")
    print(f"Video   : {video.name}")
    print(f"Image   : {image.name}\n")

    info = probe(video)
    print(f"  {info['width']}x{info['height']}  {info['fps']:.3f} fps  "
          f"{info['duration']:.2f}s  audio={info['has_audio']}  "
          f"subs={info['n_subtitle_streams']}")
    if not info["has_audio"]:
        die("the source video has no audio stream - nothing to drive the lip-sync with")

    work = proj / "_lipsync_work"
    work.mkdir(exist_ok=True)

    cuts = detect_scenes(video, args.scene_threshold, info["duration"])
    scenes = scenes_from_cuts(cuts, info["duration"])
    print(f"  {len(scenes)} scenes\n")

    words = transcribe(video, args.whisper_model) if not args.no_transcribe else []
    hit = find_phrase(words, args.phrase) if words else None
    if hit:
        print(f"  '{args.phrase}' matched at {fmt_ts(hit['start'])} "
              f"(heard: \"{hit['matched']}\", confidence {hit['score']})")
    elif words:
        print(f"  '{args.phrase}' not confidently found - set the middle segment by hand")

    print("\n  checking which scenes show a face ...")
    face_flags = []
    for (a, b) in scenes:
        face_flags.append(has_face(video, a, b))
    if all(f is None for f in face_flags):
        print("  (opencv-python not installed - skipping face check)")

    print("\n  scenes:")
    for i, ((a, b), f) in enumerate(zip(scenes, face_flags)):
        mark = {True: "FACE", False: "    ", None: " ?  "}[f]
        key = " <-- key phrase" if hit and a <= hit["start"] < b else ""
        print(f"    [{i:2d}] {fmt_ts(a)} -> {fmt_ts(b)}  ({b - a:6.2f}s)  {mark}{key}")

    if args.thumbnails:
        save_thumbnails(video, scenes, work / "thumbs")

    # ---- propose the three segments -------------------------------------
    face_idx = [i for i, f in enumerate(face_flags) if f]
    pool = face_idx if face_idx else list(range(len(scenes)))

    chosen = {}
    if pool:
        chosen["intro"] = pool[0]
    if hit:
        for i, (a, b) in enumerate(scenes):
            if a <= hit["start"] < b:
                chosen["key_step"] = i
                break
    if pool:
        chosen["outro"] = pool[-1]

    segments = []
    for name in ("intro", "key_step", "outro"):
        if name not in chosen:
            continue
        a, b = scenes[chosen[name]]
        if any(abs(s["start"] - a) < 0.01 for s in segments):
            continue
        segments.append({"name": name, "start": a, "end": b, "enabled": True})
    segments.sort(key=lambda s: s["start"])

    cfg = {
        "project_dir": str(proj).replace("\\", "/"),
        "video": args.video,
        "image": args.image,
        "output": args.output,
        "sadtalker_dir": str(Path(args.sadtalker_dir).resolve()).replace("\\", "/")
                         if args.sadtalker_dir else "",
        "source": info,
        "segments": segments,
        "fit": "cover",
        "caption_band": None,
        "encode": {"encoder": "libx264", "crf": 18, "preset": "slow"},
        "sadtalker": {
            "preprocess": "full",
            "size": 256,
            "still": False,
            "enhancer": "gfpgan",
            "expression_scale": 1.0,
            "pose_style": 0,
            "batch_size": 2,
        },
        "_analysis": {
            "scenes": [{"index": i, "start": a, "end": b, "face": f}
                       for i, ((a, b), f) in enumerate(zip(scenes, face_flags))],
            "key_phrase_hit": hit,
        },
    }

    cfg_path = proj / "config.json"
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    print("\n  proposed segments to replace:")
    for s in segments:
        print(f"    {s['name']:<9} {fmt_ts(s['start'])} -> {fmt_ts(s['end'])}  "
              f"({s['end'] - s['start']:.2f}s)")
    if len(segments) < 3:
        print("\n  NOTE: fewer than 3 segments were auto-detected. Open config.json")
        print("        and fill in the missing start/end times yourself.")
    print(f"\nWrote {cfg_path}")
    print("Check the segment times (thumbnails help), then run:  pipeline.py clips --config config.json")


# --------------------------------------------------------------------------
# clips
# --------------------------------------------------------------------------
def load_cfg(path):
    p = Path(path).resolve()
    if not p.is_file():
        die(f"config not found: {p}\nRun the 'analyze' stage first.")
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["_path"] = str(p)
    return cfg


def active_segments(cfg):
    segs = [s for s in cfg.get("segments", []) if s.get("enabled", True)]
    if not segs:
        die("no enabled segments in config.json")
    for s in segs:
        if float(s["end"]) <= float(s["start"]):
            die(f"segment '{s.get('name')}' has end <= start")
    segs.sort(key=lambda s: float(s["start"]))
    for a, b in zip(segs, segs[1:]):
        if float(b["start"]) < float(a["end"]) - 1e-6:
            die(f"segments '{a['name']}' and '{b['name']}' overlap")
    return segs


def cmd_clips(cfg, args):
    proj = Path(cfg["project_dir"])
    video = proj / cfg["video"]
    image = proj / cfg["image"]
    st_dir = Path(cfg["sadtalker_dir"] or "")
    if not st_dir.is_dir() or not (st_dir / "inference.py").is_file():
        die(f"SadTalker not found at '{st_dir}'. Set \"sadtalker_dir\" in config.json "
            f"to the folder containing inference.py")

    work = proj / "_lipsync_work"
    work.mkdir(exist_ok=True)
    st = cfg.get("sadtalker", {})
    segs = active_segments(cfg)

    print(f"Rendering {len(segs)} talking-head clip(s) with SadTalker\n")
    for s in segs:
        name = s["name"]
        start, end = float(s["start"]), float(s["end"])
        dur = end - start
        wav = work / f"{name}.wav"
        final = work / f"clip_{name}.mp4"

        if final.is_file() and not args.force:
            print(f"[{name}] already rendered ({final.name}) - use --force to redo\n")
            continue

        print(f"[{name}] {fmt_ts(start)} -> {fmt_ts(end)}  ({dur:.2f}s)")
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(video),
             "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)])

        result_dir = work / f"sadtalker_{name}"
        if result_dir.exists():
            shutil.rmtree(result_dir)
        result_dir.mkdir(parents=True)

        cmd = [sys.executable, "inference.py",
               "--driven_audio", str(wav.resolve()),
               "--source_image", str(image.resolve()),
               "--result_dir", str(result_dir.resolve()),
               "--preprocess", st.get("preprocess", "full"),
               "--size", str(st.get("size", 256)),
               "--expression_scale", str(st.get("expression_scale", 1.0)),
               "--pose_style", str(st.get("pose_style", 0)),
               "--batch_size", str(st.get("batch_size", 2))]
        if st.get("still"):
            cmd.append("--still")
        if st.get("enhancer"):
            cmd += ["--enhancer", st["enhancer"]]
        if st.get("ref_eyeblink"):
            cmd += ["--ref_eyeblink", str((proj / st["ref_eyeblink"]).resolve())]
        if st.get("cpu"):
            cmd.append("--cpu")

        print(f"  rendering (this is the slow part) ...")
        run(cmd, cwd=st_dir)

        produced = sorted(result_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
        if not produced:
            die(f"SadTalker produced no mp4 in {result_dir}")
        best = produced[-1]
        enhanced = [p for p in produced if "enhanced" in p.name.lower()]
        if enhanced:
            best = max(enhanced, key=lambda p: p.stat().st_mtime)
        shutil.copy2(best, final)

        got = probe(final)
        print(f"  -> {final.name}  ({got['width']}x{got['height']}, "
              f"{got['fps']:.2f} fps, {got['duration']:.2f}s vs {dur:.2f}s needed)")
        if got["duration"] < dur - 0.25:
            print(f"  note: clip is {dur - got['duration']:.2f}s short; "
                  f"its final frame will be held to fill the window.")
        print()

    print("All clips rendered. Next:  pipeline.py assemble --config config.json")


# --------------------------------------------------------------------------
# assemble
# --------------------------------------------------------------------------
def fit_chain(fit, w, h):
    if fit == "contain":
        return (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black")
    if fit == "stretch":
        return f"scale={w}:{h}"
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}")


def build_graph(cfg, segs, w, h, fps):
    band = cfg.get("caption_band")
    lines = []
    if band:
        lines.append("[0:v]split=2[base][bandsrc];")
        cur = "[base]"
    else:
        cur = "[0:v]"

    fit = fit_chain(cfg.get("fit", "cover"), w, h)
    for i, s in enumerate(segs, start=1):
        start, end = float(s["start"]), float(s["end"])
        dur = end - start
        lines.append(
            f"[{i}:v]fps={fps},{fit},setsar=1,format=yuv420p,"
            f"tpad=stop_mode=clone:stop_duration=5,"
            f"trim=duration={dur:.6f},setpts=PTS-STARTPTS+{start:.6f}/TB[c{i}];"
        )
        out = f"[v{i}]"
        lines.append(
            f"{cur}[c{i}]overlay=x=0:y=0:eof_action=pass:repeatlast=0:"
            f"enable='between(t,{start:.6f},{end:.6f})'{out};"
        )
        cur = out

    if band:
        by, bh = int(band["y"]), int(band["h"])
        enable = "+".join(f"between(t,{float(s['start']):.6f},{float(s['end']):.6f})"
                          for s in segs)
        lines.append(f"[bandsrc]crop={w}:{bh}:0:{by},setsar=1[band];")
        lines.append(f"{cur}[band]overlay=x=0:y={by}:enable='{enable}'[vout];")
        cur = "[vout]"

    # strip the trailing ';' on the last statement and name the final output
    graph = "\n".join(lines).rstrip().rstrip(";")
    return graph, cur


def cmd_assemble(cfg, args):
    need("ffmpeg")
    proj = Path(cfg["project_dir"])
    video = proj / cfg["video"]
    work = proj / "_lipsync_work"
    out = proj / cfg["output"]
    segs = active_segments(cfg)

    clips = []
    for s in segs:
        c = work / f"clip_{s['name']}.mp4"
        if not c.is_file():
            die(f"missing rendered clip {c}. Run the 'clips' stage first.")
        clips.append(c)

    info = cfg.get("source") or probe(video)
    w, h, fps = int(info["width"]), int(info["height"]), float(info["fps"])

    band = cfg.get("caption_band")
    if band:
        by, bh = int(band["y"]), int(band["h"])
        if by < 0 or bh <= 0 or by + bh > h:
            die(f"caption_band {{y:{by}, h:{bh}}} does not fit inside a {w}x{h} frame")
        print(f"  caption band y={by} h={bh} will be copied back from the original")

    graph, final_label = build_graph(cfg, segs, w, h, fps)
    graph_file = work / "filtergraph.txt"
    graph_file.write_text(graph, encoding="utf-8")

    enc = cfg.get("encode", {})
    encoder = args.encoder or enc.get("encoder", "libx264")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", str(video)]
    for c in clips:
        cmd += ["-i", str(c)]
    cmd += ["-filter_complex_script", str(graph_file), "-map", final_label]

    if encoder == "h264_nvenc":
        cmd += ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
                "-cq", str(enc.get("crf", 19)), "-b:v", "0"]
    elif encoder == "hevc_nvenc":
        cmd += ["-c:v", "hevc_nvenc", "-preset", "p5", "-rc", "vbr",
                "-cq", str(enc.get("crf", 22)), "-b:v", "0", "-tag:v", "hvc1"]
    else:
        cmd += ["-c:v", "libx264", "-preset", enc.get("preset", "slow"),
                "-crf", str(enc.get("crf", 18))]
    cmd += ["-pix_fmt", "yuv420p"]

    # Original audio copied bit-for-bit: timing and captions stay in sync.
    if info.get("has_audio", True):
        cmd += ["-map", "0:a?", "-c:a", "copy"]
    if info.get("n_subtitle_streams"):
        cmd += ["-map", "0:s?", "-c:s", "mov_text"]
    cmd += ["-movflags", "+faststart"]

    if args.preview:
        first = float(segs[0]["start"])
        cmd += ["-ss", f"{max(0.0, first - 2):.3f}", "-t", "15"]
        out = out.with_name(out.stem + "_PREVIEW" + out.suffix)

    cmd.append(str(out))

    print(f"\n  {len(segs)} segment(s) -> {out.name}  ({w}x{h} @ {fps:.3f} fps, {encoder})")
    run(cmd)

    if out.is_file():
        res = probe(out)
        print(f"\nDone: {out}")
        print(f"      {res['width']}x{res['height']}  {res['fps']:.3f} fps  "
              f"{res['duration']:.2f}s   (source was {info['duration']:.2f}s)")
        if abs(res["duration"] - float(info["duration"])) > 0.5 and not args.preview:
            print("      WARNING: duration drifted from the source - check the result.")
    else:
        die("ffmpeg reported success but the output file is missing")


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="stage", required=True)

    a = sub.add_parser("analyze", help="probe, cut-detect, transcribe, write config.json")
    a.add_argument("--project-dir", required=True)
    a.add_argument("--video", default="bushra_ep1.mp4")
    a.add_argument("--image", required=True)
    a.add_argument("--output", default="bushra_ep1_talking.mp4")
    a.add_argument("--sadtalker-dir", default="")
    a.add_argument("--scene-threshold", type=float, default=0.30)
    a.add_argument("--whisper-model", default="small")
    a.add_argument("--phrase", default=KEY_PHRASE)
    a.add_argument("--no-transcribe", action="store_true")
    a.add_argument("--thumbnails", action="store_true", default=True)

    c = sub.add_parser("clips", help="render the talking-head clips")
    c.add_argument("--config", default="config.json")
    c.add_argument("--force", action="store_true", help="re-render clips that already exist")

    s = sub.add_parser("assemble", help="splice the clips back into the episode")
    s.add_argument("--config", default="config.json")
    s.add_argument("--encoder", default=None,
                   choices=["libx264", "h264_nvenc", "hevc_nvenc"])
    s.add_argument("--preview", action="store_true",
                   help="render only ~15s around the first segment")

    al = sub.add_parser("all", help="clips + assemble")
    al.add_argument("--config", default="config.json")
    al.add_argument("--force", action="store_true")
    al.add_argument("--encoder", default=None,
                    choices=["libx264", "h264_nvenc", "hevc_nvenc"])
    al.add_argument("--preview", action="store_true")

    args = ap.parse_args()

    if args.stage == "analyze":
        cmd_analyze(args)
    elif args.stage == "clips":
        cmd_clips(load_cfg(args.config), args)
    elif args.stage == "assemble":
        cmd_assemble(load_cfg(args.config), args)
    else:
        cfg = load_cfg(args.config)
        cmd_clips(cfg, args)
        cmd_assemble(cfg, args)


if __name__ == "__main__":
    main()

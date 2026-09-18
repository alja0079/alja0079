#!/usr/bin/env python3
"""Download SadTalker checkpoints on Windows (no wget/bash needed).

Parses SadTalker's own scripts/download_models.sh so the URL list always
matches whatever revision of the repo you cloned.
"""
import argparse
import re
import sys
import urllib.request
from pathlib import Path

WGET_RE = re.compile(r"""wget\s+(?:-\S+\s+)*['"]?(https?://\S+?)['"]?\s+-O\s+['"]?(\S+?)['"]?\s*$""")

# Fallback if the shell script is missing or its format changed.
FALLBACK = [
    ("https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar",
     "./checkpoints/mapping_00109-model.pth.tar"),
    ("https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00229-model.pth.tar",
     "./checkpoints/mapping_00229-model.pth.tar"),
    ("https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors",
     "./checkpoints/SadTalker_V0.0.2_256.safetensors"),
    ("https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_512.safetensors",
     "./checkpoints/SadTalker_V0.0.2_512.safetensors"),
    ("https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth",
     "./gfpgan/weights/alignment_WFLW_4HG.pth"),
    ("https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth",
     "./gfpgan/weights/detection_Resnet50_Final.pth"),
    ("https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
     "./gfpgan/weights/GFPGANv1.4.pth"),
    ("https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth",
     "./gfpgan/weights/realesr-general-x4v3.pth"),
]


def parse_script(script: Path):
    pairs = []
    for raw in script.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.startswith("wget"):
            continue  # skip comments / mkdir / legacy links
        m = WGET_RE.match(line)
        if m:
            pairs.append((m.group(1), m.group(2)))
    return pairs


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f}{unit}"
        n /= 1024


def download(url: str, dest: Path):
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  [skip] {dest.name} already present ({human(dest.stat().st_size)})")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  [get ] {dest.name}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if total:
                pct = 100.0 * got / total
                print(f"\r         {human(got)} / {human(total)} ({pct:4.1f}%)", end="", flush=True)
        print()
    tmp.replace(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sadtalker-dir", required=True, help="path to the cloned SadTalker repo")
    args = ap.parse_args()

    root = Path(args.sadtalker_dir).resolve()
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")

    script = root / "scripts" / "download_models.sh"
    pairs = parse_script(script) if script.is_file() else []
    if pairs:
        print(f"Using URL list from {script}  ({len(pairs)} files)")
    else:
        print("Could not parse scripts/download_models.sh - using built-in fallback list")
        pairs = FALLBACK

    for url, rel in pairs:
        dest = (root / rel.lstrip("./")).resolve()
        try:
            download(url, dest)
        except Exception as e:
            print(f"  [FAIL] {rel}: {e}")
            print("         Re-run this script to resume; partial files are discarded.")
            sys.exit(1)

    print("\nAll checkpoints present.")


if __name__ == "__main__":
    main()

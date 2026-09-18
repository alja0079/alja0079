#!/usr/bin/env python3
"""Apply the compatibility fixes SadTalker needs on a modern CUDA/PyTorch stack.

SadTalker's last release predates several breaking changes in its dependencies.
Without these three patches it crashes on import or on the first mel-spectrogram.
Every patch is idempotent - re-running is safe.

  1. torchvision >= 0.17 removed `torchvision.transforms.functional_tensor`,
     which basicsr (pulled in by gfpgan) imports at module level.
  2. librosa >= 0.10 made `librosa.filters.mel()` keyword-only; SadTalker calls
     it positionally in src/utils/audio.py.
  3. torch >= 2.6 flipped `torch.load(weights_only=...)` to True by default,
     which rejects SadTalker's .pth.tar checkpoints.
"""
import argparse
import importlib.util
import re
import sys
from pathlib import Path

TORCH_LOAD_SHIM = '''
# --- begin bushra-lipsync compat shim (torch>=2.6 weights_only default) ---
import torch as _bl_torch
if not getattr(_bl_torch, "_bl_load_patched", False):
    _bl_orig_load = _bl_torch.load

    def _bl_load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _bl_orig_load(*args, **kwargs)

    _bl_torch.load = _bl_load
    _bl_torch._bl_load_patched = True
# --- end bushra-lipsync compat shim ---
'''.lstrip("\n")

SHIM_MARKER = "bushra-lipsync compat shim"


def patch_functional_tensor(verbose=True):
    """Rewrite `torchvision.transforms.functional_tensor` imports in site-packages."""
    changed = []
    for pkg in ("basicsr", "facexlib", "gfpgan", "realesrgan"):
        spec = importlib.util.find_spec(pkg)
        if spec is None or not spec.submodule_search_locations:
            continue
        root = Path(list(spec.submodule_search_locations)[0])
        for py in root.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if "torchvision.transforms.functional_tensor" not in text:
                continue
            new = text.replace(
                "torchvision.transforms.functional_tensor",
                "torchvision.transforms.functional",
            )
            py.write_text(new, encoding="utf-8")
            changed.append(py)
    if verbose:
        if changed:
            for p in changed:
                print(f"  [patched] {p}")
        else:
            print("  [ok] no functional_tensor imports found (already patched or not needed)")
    return changed


def patch_librosa_mel(sadtalker_dir: Path, verbose=True):
    """Make the librosa.filters.mel() call keyword-based."""
    audio_py = sadtalker_dir / "src" / "utils" / "audio.py"
    if not audio_py.is_file():
        if verbose:
            print(f"  [skip] {audio_py} not found")
        return False
    text = audio_py.read_text(encoding="utf-8")

    # librosa.filters.mel(hp.sample_rate, hp.n_fft, n_mels=..., ...)
    pattern = re.compile(
        r"librosa\.filters\.mel\(\s*(?!sr\s*=)([^,()]+?)\s*,\s*(?!n_fft\s*=)([^,()]+?)\s*,")
    new, n = pattern.subn(r"librosa.filters.mel(sr=\1, n_fft=\2,", text)
    if n == 0:
        if verbose:
            print("  [ok] librosa.filters.mel already uses keyword args")
        return False
    audio_py.write_text(new, encoding="utf-8")
    if verbose:
        print(f"  [patched] {audio_py} ({n} call site{'s' if n != 1 else ''})")
    return True


def patch_torch_load(sadtalker_dir: Path, verbose=True):
    """Inject a torch.load shim at the top of inference.py."""
    inf = sadtalker_dir / "inference.py"
    if not inf.is_file():
        if verbose:
            print(f"  [skip] {inf} not found")
        return False
    text = inf.read_text(encoding="utf-8")
    if SHIM_MARKER in text:
        if verbose:
            print("  [ok] torch.load shim already present in inference.py")
        return False

    lines = text.splitlines(keepends=True)
    # Only a shebang / encoding cookie / leading comments may precede the shim:
    # it must run before any other import touches torch.
    insert_at = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s == "" or s.startswith("#"):
            insert_at = i + 1
            continue
        break
    lines.insert(insert_at, TORCH_LOAD_SHIM + "\n")
    inf.write_text("".join(lines), encoding="utf-8")
    if verbose:
        print(f"  [patched] {inf}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sadtalker-dir", required=True)
    args = ap.parse_args()
    root = Path(args.sadtalker_dir).resolve()
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")

    print("1/3 torchvision.transforms.functional_tensor ->  functional")
    patch_functional_tensor()
    print("2/3 librosa.filters.mel keyword args")
    patch_librosa_mel(root)
    print("3/3 torch.load(weights_only=False) shim")
    patch_torch_load(root)
    print("\nPatching complete.")


if __name__ == "__main__":
    main()

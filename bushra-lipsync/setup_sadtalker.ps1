<#
  One-shot SadTalker install for Windows + NVIDIA GPU.

  Creates an isolated venv, installs a CUDA build of PyTorch matched to your
  GPU, clones SadTalker, downloads its checkpoints, and applies the three
  compatibility patches it needs on a modern dependency stack.

  Usage:
      powershell -ExecutionPolicy Bypass -File .\setup_sadtalker.ps1
      powershell -ExecutionPolicy Bypass -File .\setup_sadtalker.ps1 -InstallDir "D:\ai\SadTalker"
#>
param(
    [string]$InstallDir = "$env:USERPROFILE\ai\SadTalker",
    [string]$Python     = "",
    [switch]$SkipModels
)

$ErrorActionPreference = "Stop"

function Step($n, $msg) { Write-Host "`n[$n] $msg" -ForegroundColor Cyan }
function Warn($msg)     { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Ok($msg)       { Write-Host "  + $msg" -ForegroundColor Green }
function Fail($msg)     { Write-Host "`nERROR: $msg" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------- 1. prereqs
Step 1 "Checking prerequisites"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail "git not found. Install it:  winget install --id Git.Git -e"
}
Ok "git found"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Fail "ffmpeg not found on PATH. Install it, then OPEN A NEW TERMINAL:
       winget install --id Gyan.FFmpeg -e"
}
Ok "ffmpeg found"

# Prefer 3.10: basicsr / gfpgan are unreliable on 3.12+.
$VerProbe = "import sys;print('%d.%d'%sys.version_info[:2])"

function Get-PyVersion($exe, $arg) {
    try {
        if ($arg) { $v = & $exe $arg -c $VerProbe 2>$null } else { $v = & $exe -c $VerProbe 2>$null }
        if ($LASTEXITCODE -eq 0 -and $v) { return "$v".Trim() }
    } catch { }
    return ""
}

$PyCmd = ""; $PyArg = $null; $PyVer = ""
if ($Python -eq "") {
    foreach ($cand in @(@("py", "-3.10"), @("py", "-3.11"), @("python", $null))) {
        if (-not (Get-Command $cand[0] -ErrorAction SilentlyContinue)) { continue }
        $v = Get-PyVersion $cand[0] $cand[1]
        if ($v) { $PyCmd = $cand[0]; $PyArg = $cand[1]; $PyVer = $v; break }
    }
} else {
    $parts = $Python.Split(" ", 2)
    $PyCmd = $parts[0]
    if ($parts.Count -gt 1) { $PyArg = $parts[1] }
    $PyVer = Get-PyVersion $PyCmd $PyArg
}
if ($PyCmd -eq "" -or $PyVer -eq "") {
    Fail "No usable Python found. Install Python 3.10:  winget install --id Python.Python.3.10 -e"
}
Ok "python: $PyCmd $PyArg (version $PyVer)"
if ($PyVer -eq "3.12" -or $PyVer -eq "3.13") {
    Warn "Python $PyVer is newer than SadTalker's dependencies expect. If the install"
    Warn "fails, install 3.10 and re-run with:  -Python 'py -3.10'"
}

# ------------------------------------------------------------------- 2. GPU
Step 2 "Detecting GPU"

$gpuName = ""
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $gpuName = (nvidia-smi --query-gpu=name --format=csv,noheader | Select-Object -First 1)
    $driver  = (nvidia-smi --query-gpu=driver_version --format=csv,noheader | Select-Object -First 1)
    Ok "$gpuName (driver $driver)"
} else {
    Warn "nvidia-smi not found. Continuing, but rendering will fall back to CPU (very slow)."
}

# Blackwell (RTX 50-series / RTX PRO) has no kernels in cu124 builds.
if ($gpuName -match "RTX (50\d\d|PRO)" -or $gpuName -match "Blackwell") {
    $TorchIndex = "https://download.pytorch.org/whl/cu128"
    $TorchPkgs  = @("torch==2.7.1", "torchvision==0.22.1", "torchaudio==2.7.1")
    Ok "using CUDA 12.8 wheels (Blackwell-class GPU)"
} else {
    $TorchIndex = "https://download.pytorch.org/whl/cu124"
    $TorchPkgs  = @("torch==2.5.1", "torchvision==0.20.1", "torchaudio==2.5.1")
    Ok "using CUDA 12.4 wheels"
}

# ------------------------------------------------------------ 3. clone repo
Step 3 "Cloning SadTalker into $InstallDir"

if (Test-Path (Join-Path $InstallDir "inference.py")) {
    Ok "already cloned"
} else {
    $parent = Split-Path -Parent $InstallDir
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    git clone --depth 1 https://github.com/OpenTalker/SadTalker.git $InstallDir
    if ($LASTEXITCODE -ne 0) { Fail "git clone failed" }
    Ok "cloned"
}

# ----------------------------------------------------------------- 4. venv
Step 4 "Creating virtual environment"

$VenvDir = Join-Path $InstallDir ".venv"
$PyExe   = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $PyExe)) {
    if ($PyArg) { & $PyCmd $PyArg -m venv $VenvDir } else { & $PyCmd -m venv $VenvDir }
    if (-not (Test-Path $PyExe)) { Fail "venv creation failed" }
}
Ok $PyExe
& $PyExe -m pip install --quiet --upgrade pip setuptools wheel

# ------------------------------------------------------------- 5. pytorch
Step 5 "Installing PyTorch (large download, be patient)"
& $PyExe -m pip install --index-url $TorchIndex @TorchPkgs
if ($LASTEXITCODE -ne 0) { Fail "PyTorch install failed" }

$cudaOk = & $PyExe -c "import torch;print(torch.cuda.is_available())"
if ($cudaOk.Trim() -eq "True") {
    $dev = & $PyExe -c "import torch;print(torch.cuda.get_device_name(0))"
    Ok "CUDA active: $dev"
} else {
    Warn "torch.cuda.is_available() is False - rendering will use the CPU and be very slow."
    Warn "Usually means the NVIDIA driver is older than the CUDA build. Update your driver."
}

# -------------------------------------------------------- 6. other packages
Step 6 "Installing SadTalker dependencies"

# numpy is held below 2.0 on purpose: basicsr/gfpgan break on the 2.x ABI.
$core = @(
    "numpy==1.26.4", "scipy==1.11.4",
    "librosa==0.10.2.post1", "resampy==0.4.3", "numba>=0.59",
    "imageio==2.34.2", "imageio-ffmpeg==0.5.1", "av",
    "opencv-python==4.10.0.84", "scikit-image==0.22.0",
    "kornia==0.7.3", "yacs==0.1.8", "pyyaml", "joblib",
    "pydub==0.25.1", "tqdm", "safetensors"
)
& $PyExe -m pip install @core
if ($LASTEXITCODE -ne 0) { Fail "core dependency install failed" }
Ok "core dependencies installed"

# basicsr's setup.py imports torch, so build isolation has to be off.
$enh = @("basicsr==1.4.2", "facexlib==0.3.0", "gfpgan==1.3.8", "realesrgan==0.3.0")
& $PyExe -m pip install --no-build-isolation @enh
if ($LASTEXITCODE -ne 0) {
    Warn "face-enhancer packages failed to install."
    Warn 'You can still run the pipeline - set "enhancer": null in config.json.'
} else {
    Ok "face enhancer (GFPGAN) installed"
}

# Optional: lets 'analyze' find the 'Now the key step' scene automatically.
& $PyExe -m pip install faster-whisper
if ($LASTEXITCODE -ne 0) { Warn "faster-whisper failed; 'analyze' will skip transcription." }
else { Ok "faster-whisper installed" }

# ------------------------------------------------------------ 7. checkpoints
if (-not $SkipModels) {
    Step 7 "Downloading model checkpoints (~2 GB)"
    & $PyExe (Join-Path $PSScriptRoot "download_models.py") --sadtalker-dir $InstallDir
    if ($LASTEXITCODE -ne 0) { Fail "checkpoint download failed - re-run this script to resume" }
} else {
    Step 7 "Skipping checkpoint download (-SkipModels)"
}

# --------------------------------------------------------------- 8. patches
Step 8 "Applying compatibility patches"
& $PyExe (Join-Path $PSScriptRoot "patch_sadtalker.py") --sadtalker-dir $InstallDir
if ($LASTEXITCODE -ne 0) { Fail "patching failed" }

# ----------------------------------------------------------------- summary
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " SadTalker is ready." -ForegroundColor Green
Write-Host "============================================================"
Write-Host " Install dir : $InstallDir"
Write-Host " Python      : $PyExe"
Write-Host ""
Write-Host " Next - from this folder, run the three pipeline stages with"
Write-Host " that SAME python so it can import torch:"
Write-Host ""
Write-Host "   & '$PyExe' pipeline.py analyze ``"
Write-Host "       --project-dir 'C:\Users\K\Downloads\Bushra Episode 1' ``"
Write-Host "       --video bushra_ep1.mp4 ``"
Write-Host "       --image 'ChatGPT_Image_Sep_18__2026__01_28_13_PM.png' ``"
Write-Host "       --sadtalker-dir '$InstallDir'"
Write-Host ""
Write-Host "   (check the segment times in config.json, then)"
Write-Host ""
Write-Host "   & '$PyExe' pipeline.py all --config 'C:\Users\K\Downloads\Bushra Episode 1\config.json'"
Write-Host ""

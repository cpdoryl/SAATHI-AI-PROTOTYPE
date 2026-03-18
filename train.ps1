# ============================================================
#  Saath AI — Unsloth Llama-3 Training Automation (Windows)
#  Usage:
#    .\train.ps1              # full pipeline (setup + train)
#    .\train.ps1 --setup      # install dependencies only
#    .\train.ps1 --train-only # skip setup, run training only
#    .\train.ps1 --skip-ollama # skip Ollama import at the end
# ============================================================
param(
    [switch]$Setup,
    [switch]$TrainOnly,
    [switch]$SkipOllama,
    [string]$Dataset   = ".\Meta model pattern detector\scripts\dataset.jsonl",
    [string]$Output    = ".\output\llama3_finetuned",
    [string]$GgufDir   = ".\output\gguf",
    [string]$OllamaName = "saath-llama3",
    [int]$Epochs       = 3
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$TrainScript = Join-Path $ScriptDir "Meta model pattern detector\scripts\train_unsloth_llama3.py"
$VenvDir     = Join-Path $ScriptDir ".venv-unsloth"
$PythonExe   = "python"

# ── Colours ──────────────────────────────────────────────────────────────────
function Write-Step($msg)  { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)    { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail($msg)  { Write-Host "  [FAIL] $msg" -ForegroundColor Red; exit 1 }

# ── Check Python ─────────────────────────────────────────────────────────────
Write-Step "Checking prerequisites"
try {
    $pyVer = & python --version 2>&1
    Write-OK "Python: $pyVer"
} catch {
    Write-Fail "Python not found. Install Python 3.10-3.12 and add to PATH."
}

# Check CUDA
$cudaAvail = & python -c "import torch; print(torch.cuda.is_available())" 2>$null
if ($cudaAvail -eq "True") {
    $gpuName = & python -c "import torch; print(torch.cuda.get_device_name(0))" 2>$null
    Write-OK "CUDA GPU: $gpuName"
} else {
    Write-Warn "CUDA not detected — will try to install torch with CUDA. If training fails, install CUDA 12.x manually."
}

# ── Venv setup ────────────────────────────────────────────────────────────────
if (-not $TrainOnly) {
    Write-Step "Setting up virtual environment at $VenvDir"

    if (-not (Test-Path $VenvDir)) {
        Write-Host "  Creating venv..."
        & python -m venv $VenvDir
        Write-OK "Venv created"
    } else {
        Write-OK "Venv already exists"
    }

    $PythonExe = Join-Path $VenvDir "Scripts\python.exe"
    $PipExe    = Join-Path $VenvDir "Scripts\pip.exe"

    Write-Step "Installing / upgrading dependencies"
    Write-Host "  This may take 5-10 minutes on first run..."

    # Upgrade pip first
    & $PythonExe -m pip install --upgrade pip --quiet

    # Install PyTorch with CUDA 12.1 support (compatible with driver 577+)
    Write-Host "  Installing PyTorch 2.x + CUDA 12.1..."
    & $PipExe install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet
    if ($LASTEXITCODE -ne 0) { Write-Fail "PyTorch install failed." }
    Write-OK "PyTorch installed"

    # Install Unsloth (auto-selects correct CUDA variant)
    Write-Host "  Installing Unsloth..."
    & $PipExe install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" --quiet
    if ($LASTEXITCODE -ne 0) {
        # Fallback to PyPI release
        Write-Warn "Git install failed, trying PyPI..."
        & $PipExe install unsloth --quiet
    }
    Write-OK "Unsloth installed"

    # Install remaining training deps
    Write-Host "  Installing training dependencies..."
    & $PipExe install `
        transformers>=4.40 `
        trl>=0.8.6 `
        peft>=0.10 `
        accelerate>=0.29 `
        bitsandbytes>=0.43 `
        datasets>=2.18 `
        sentencepiece `
        protobuf `
        --quiet
    if ($LASTEXITCODE -ne 0) { Write-Fail "Dependency install failed." }
    Write-OK "All dependencies installed"
} else {
    # Use venv if it exists, otherwise system python
    $venvPy = Join-Path $VenvDir "Scripts\python.exe"
    if (Test-Path $venvPy) {
        $PythonExe = $venvPy
        Write-OK "Using existing venv: $VenvDir"
    } else {
        Write-OK "Using system Python"
    }
}

if ($Setup) {
    Write-Host "`n[DONE] Setup complete. Run .\train.ps1 --train-only to start training." -ForegroundColor Green
    exit 0
}

# ── Validate dataset ──────────────────────────────────────────────────────────
Write-Step "Validating dataset"
$datasetPath = Join-Path $ScriptDir $Dataset.TrimStart(".\")
if (-not (Test-Path $datasetPath)) {
    Write-Fail "Dataset not found: $datasetPath`n  Place your dataset.jsonl at that path, or pass -Dataset <path>"
}
$lineCount = (Get-Content $datasetPath | Measure-Object -Line).Lines
Write-OK "Dataset: $datasetPath ($lineCount examples)"

# ── Run training ──────────────────────────────────────────────────────────────
Write-Step "Starting Unsloth fine-tuning"
Write-Host "  Script  : $TrainScript"
Write-Host "  Epochs  : $Epochs"
Write-Host "  Output  : $Output"
Write-Host "  GGUF    : $GgufDir"
Write-Host ""

$startTime = Get-Date

& $PythonExe $TrainScript `
    --dataset  $datasetPath `
    --output   (Join-Path $ScriptDir $Output.TrimStart(".\")) `
    --gguf_dir (Join-Path $ScriptDir $GgufDir.TrimStart(".\")) `
    --epochs   $Epochs

if ($LASTEXITCODE -ne 0) { Write-Fail "Training script exited with error $LASTEXITCODE" }

$elapsed = (Get-Date) - $startTime
Write-OK "Training finished in $($elapsed.ToString('hh\:mm\:ss'))"

# ── Import into Ollama ────────────────────────────────────────────────────────
if (-not $SkipOllama) {
    Write-Step "Importing model into Ollama as '$OllamaName'"

    $ggufAbsDir = Join-Path $ScriptDir $GgufDir.TrimStart(".\")
    $ggufFile   = Get-ChildItem $ggufAbsDir -Filter "*.gguf" -ErrorAction SilentlyContinue | Select-Object -First 1

    if (-not $ggufFile) {
        Write-Warn "No .gguf file found in $ggufAbsDir — skipping Ollama import"
        Write-Warn "Run manually: ollama create $OllamaName -f Modelfile"
    } else {
        $ggufPath    = $ggufFile.FullName
        $modelfilePath = Join-Path $ScriptDir "Modelfile"

        # Write Modelfile
        @"
FROM $ggufPath

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"

SYSTEM """You are a helpful AI assistant created by Saath AI."""
"@ | Set-Content $modelfilePath -Encoding UTF8

        Write-Host "  Modelfile written: $modelfilePath"
        Write-Host "  Running: ollama create $OllamaName ..."

        $ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
        if (-not (Test-Path $ollamaExe)) { $ollamaExe = "ollama" }

        & $ollamaExe create $OllamaName -f $modelfilePath
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Model imported into Ollama as '$OllamaName'"
            Write-Host "`n  Run it now: ollama run $OllamaName" -ForegroundColor Green
        } else {
            Write-Warn "Ollama import failed. Run manually:"
            Write-Warn "  ollama create $OllamaName -f $modelfilePath"
        }
    }
}

Write-Host "`n[ALL DONE] Full training pipeline complete!" -ForegroundColor Green

# SAATHI AI — Autonomous Model Training Pipeline
# Runs without any user interaction. Creates Ollama CTO model immediately,
# then starts background fine-tuning while you're away.
#
# Usage:
#   cd "c:\saath ai prototype"
#   .\fine_tune\run_pipeline.ps1
#
# The script will:
#   Step 1: Create saathi-cto Ollama model IMMEDIATELY (uses system prompt, ~10 sec)
#   Step 2: Set up Python virtual environment for fine-tuning
#   Step 3: Install all training dependencies
#   Step 4: Generate training data from CTO knowledge base
#   Step 5: Run QLoRA fine-tuning (runs for hours — you can be away)
#   Step 6: Attempt GGUF export and update Ollama model

param(
    [switch]$QuickTest,       # Run only 5 training steps as smoke test
    [switch]$SkipInstall,     # Skip pip install (if already done)
    [switch]$OllamaOnly       # Only create Ollama model, skip fine-tuning
)

$ErrorActionPreference = "Continue"
$StartTime = Get-Date
$ProjectRoot = "c:\saath ai prototype"
$FineTuneDir = "$ProjectRoot\fine_tune"
$LogFile = "$FineTuneDir\training_log.txt"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] [$Level] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Write-Banner {
    param([string]$Title)
    $border = "=" * 60
    Write-Host ""
    Write-Host $border -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host $border -ForegroundColor Cyan
    Write-Host ""
}

# Create log file
New-Item -ItemType File -Path $LogFile -Force | Out-Null
Write-Log "Pipeline started. Project root: $ProjectRoot"

# ─── STEP 1: CREATE OLLAMA MODEL IMMEDIATELY ─────────────────────────────────
Write-Banner "STEP 1: Creating saathi-cto Ollama model"

$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (!(Test-Path $ollamaExe)) {
    $ollamaExe = "C:\Users\B P Verma\AppData\Local\Programs\Ollama\ollama.exe"
}

if (Test-Path $ollamaExe) {
    Write-Log "Ollama found at: $ollamaExe"
    
    # Start Ollama server if not running
    $ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if (!$ollamaProcess) {
        Write-Log "Starting Ollama server..."
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 4
    } else {
        Write-Log "Ollama server already running"
    }
    
    # Create custom model from Modelfile
    Write-Log "Creating saathi-cto model from Modelfile (this takes ~15 seconds)..."
    $modelfileArg = "$FineTuneDir\Modelfile"
    
    try {
        & $ollamaExe create saathi-cto -f $modelfileArg 2>&1 | ForEach-Object { Write-Log $_ }
        Write-Log "SUCCESS: saathi-cto model created in Ollama!" -Level "SUCCESS"
        Write-Host ""
        Write-Host "  ✓ IMMEDIATE RESULT: Your CTO model is ready NOW!" -ForegroundColor Green
        Write-Host "  Test it with: ollama run saathi-cto" -ForegroundColor Green
        Write-Host "  Ask it: 'What are the known TODOs in the codebase?'" -ForegroundColor Green
        Write-Host ""
    } catch {
        Write-Log "Warning: Ollama model creation failed: $_" -Level "WARN"
    }
} else {
    Write-Log "Ollama not found at expected path. Skipping model creation." -Level "WARN"
    Write-Log "Install Ollama first, then run: ollama create saathi-cto -f fine_tune\Modelfile"
}

if ($OllamaOnly) {
    Write-Log "OllamaOnly flag set. Stopping after Ollama model creation."
    Write-Host ""
    Write-Host "Ollama model created. Use 'ollama run saathi-cto' to chat." -ForegroundColor Green
    exit 0
}

# ─── STEP 2: SETUP PYTHON ENVIRONMENT ────────────────────────────────────────
Write-Banner "STEP 2: Setting up Python environment"

$VenvPath = "$FineTuneDir\.venv-train"

if (!(Test-Path $VenvPath) -or !$SkipInstall) {
    Write-Log "Creating virtual environment at $VenvPath ..."
    python -m venv $VenvPath 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Failed to create venv. Is Python installed?" -Level "ERROR"
        exit 1
    }
    Write-Log "Virtual environment created."
} else {
    Write-Log "Virtual environment exists, skipping creation."
}

$PipExe = "$VenvPath\Scripts\pip.exe"
$PythonExe = "$VenvPath\Scripts\python.exe"

# Verify Python
& $PythonExe --version 2>&1 | ForEach-Object { Write-Log $_ }

# ─── STEP 3: INSTALL DEPENDENCIES ────────────────────────────────────────────
if (!$SkipInstall) {
    Write-Banner "STEP 3: Installing training dependencies"
    Write-Log "This will download ~5GB of packages. Please wait..."
    
    # Upgrade pip first
    Write-Log "Upgrading pip..."
    & $PipExe install --upgrade pip 2>&1 | Select-Object -Last 3 | ForEach-Object { Write-Log $_ }
    
    # Install PyTorch with CUDA first (must be before other packages)
    Write-Log "Installing PyTorch with CUDA 12.1 support..."
    & $PipExe install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 2>&1 | 
        Where-Object { $_ -match "Successfully|Error|Warning" } | 
        ForEach-Object { Write-Log $_ }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "PyTorch CUDA install failed. Trying CPU version..." -Level "WARN"
        & $PipExe install torch torchvision torchaudio 2>&1 | 
            Where-Object { $_ -match "Successfully|Error" } | 
            ForEach-Object { Write-Log $_ }
    }
    
    # Verify CUDA
    & $PythonExe -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')" 2>&1 | ForEach-Object { Write-Log "  $_" }
    
    # Install bitsandbytes (Windows CUDA version)
    Write-Log "Installing bitsandbytes (Windows CUDA)..."
    & $PipExe install bitsandbytes --prefer-binary 2>&1 | 
        Where-Object { $_ -match "Successfully|Error|already" } | 
        ForEach-Object { Write-Log $_ }
    
    # Install remaining packages
    Write-Log "Installing HuggingFace stack (transformers, peft, trl, datasets)..."
    & $PipExe install -r "$FineTuneDir\requirements_train.txt" 2>&1 | 
        Where-Object { $_ -match "Successfully|Error|already" } | 
        ForEach-Object { Write-Log $_ }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Some packages may have failed. Attempting to continue..." -Level "WARN"
    } else {
        Write-Log "All dependencies installed successfully."
    }
}

# ─── STEP 4: GENERATE TRAINING DATA ──────────────────────────────────────────
Write-Banner "STEP 4: Generating training data"

Write-Log "Running generate_training_data.py..."
& $PythonExe "$FineTuneDir\generate_training_data.py" 2>&1 | ForEach-Object { Write-Log $_ }

if ($LASTEXITCODE -ne 0) {
    Write-Log "Data generation failed." -Level "ERROR"
    exit 1
}

$TrainFile = "$FineTuneDir\data\saathi_cto_train.jsonl"
if (Test-Path $TrainFile) {
    $lineCount = (Get-Content $TrainFile | Measure-Object -Line).Lines
    Write-Log "Training data ready: $lineCount examples"
} else {
    Write-Log "Training data file not found after generation." -Level "ERROR"
    exit 1
}

# ─── STEP 5: RUN FINE-TUNING ─────────────────────────────────────────────────
Write-Banner "STEP 5: Running QLoRA fine-tuning"

Write-Log "Model: Qwen/Qwen2.5-Coder-7B-Instruct (4-bit QLoRA)"
Write-Log "NOTE: First run will download ~14GB of model weights from HuggingFace"
Write-Log "This download needs to happen only once."
Write-Log "Training will run for several hours. Check training_log.txt for progress."
Write-Log ""

$TrainArgs = @("$FineTuneDir\train_cto_model.py")
if ($QuickTest) {
    $TrainArgs += "--quick-test"
    Write-Log "QUICK TEST MODE: Only 5 steps"
}

# Run training — captures output to log
& $PythonExe @TrainArgs 2>&1 | ForEach-Object { 
    Write-Log $_
    # Show progress lines in console too
    if ($_ -match "Step|loss|eval|Saving|ERROR|WARNING") {
        Write-Host "  $_" -ForegroundColor $(if ($_ -match "ERROR") {"Red"} elseif ($_ -match "WARNING") {"Yellow"} else {"White"})
    }
}

$TrainingExitCode = $LASTEXITCODE
if ($TrainingExitCode -ne 0) {
    Write-Log "Training exited with code $TrainingExitCode" -Level "WARN"
    Write-Log "Check log for details. Partial results may be in fine_tune/outputs/"
} else {
    Write-Log "Training completed successfully!"
}

# ─── STEP 6: UPDATE OLLAMA MODEL ─────────────────────────────────────────────
Write-Banner "STEP 6: Updating Ollama model"

$LoraOutput = "$FineTuneDir\outputs\saathi-cto-lora"
$TrainedModelfilePath = "$FineTuneDir\Modelfile_trained"

if (Test-Path $LoraOutput) {
    Write-Log "LoRA adapter saved at: $LoraOutput"
    
    if (Test-Path $ollamaExe) {
        # Check if GGUF file was created
        $GgufFile = "$FineTuneDir\outputs\gguf\saathi-cto.gguf"
        if (Test-Path $GgufFile) {
            Write-Log "GGUF model found. Creating updated saathi-cto-trained Ollama model..."
            & $ollamaExe create saathi-cto-trained -f $TrainedModelfilePath 2>&1 | ForEach-Object { Write-Log $_ }
            Write-Log "Updated model available as: saathi-cto-trained"
            Write-Host ""
            Write-Host "  ✓ FINE-TUNED MODEL READY!" -ForegroundColor Green
            Write-Host "  Use it with: ollama run saathi-cto-trained" -ForegroundColor Green
        } else {
            Write-Log "GGUF file not found. Manual GGUF conversion needed." -Level "WARN"
            Write-Log "See instructions printed during training (Step 5) for llama.cpp conversion."
        }
    }
} else {
    Write-Log "LoRA output not found at expected path." -Level "WARN"
}

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
Write-Banner "PIPELINE SUMMARY"

$Duration = (Get-Date) - $StartTime
Write-Log "Total time: $([math]::Round($Duration.TotalMinutes, 1)) minutes"
Write-Log ""
Write-Log "MODELS AVAILABLE NOW:"

if (Test-Path $ollamaExe) {
    $models = & $ollamaExe list 2>&1
    $models | ForEach-Object { Write-Log "  $_" }
}

Write-Log ""
Write-Log "TO USE YOUR CTO MODEL:"
Write-Log "  Immediate (system-prompt based):  ollama run saathi-cto"
Write-Log "  Fine-tuned (if training succeeded): ollama run saathi-cto-trained"
Write-Log ""
Write-Log "IN VS CODE (Continue extension):"
Write-Log "  Open Continue sidebar → Model dropdown → 'saathi-cto'"
Write-Log "  (Add it to ~/.continue/config.json if not listed automatically)"
Write-Log ""
Write-Log "Full log saved to: $LogFile"

Write-Host ""
Write-Host "Pipeline complete! See $LogFile for full details." -ForegroundColor Cyan

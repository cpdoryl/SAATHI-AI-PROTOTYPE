#!/usr/bin/env bash
# ============================================================
#  Saath AI — Unsloth Llama-3 Training Automation (Linux/WSL/Git Bash)
#  Usage:
#    bash train.sh              # full pipeline
#    bash train.sh --setup      # install deps only
#    bash train.sh --train-only # skip setup
#    bash train.sh --skip-ollama
# ============================================================

set -e

# ── Defaults ─────────────────────────────────────────────────────────────────
SETUP=false
TRAIN_ONLY=false
SKIP_OLLAMA=false
DATASET="./Meta model pattern detector/scripts/dataset.jsonl"
OUTPUT="./output/llama3_finetuned"
GGUF_DIR="./output/gguf"
OLLAMA_NAME="saath-llama3"
EPOCHS=3

# ── Parse args ────────────────────────────────────────────────────────────────
for arg in "$@"; do
  case $arg in
    --setup)        SETUP=true ;;
    --train-only)   TRAIN_ONLY=true ;;
    --skip-ollama)  SKIP_OLLAMA=true ;;
    --dataset=*)    DATASET="${arg#*=}" ;;
    --output=*)     OUTPUT="${arg#*=}" ;;
    --gguf-dir=*)   GGUF_DIR="${arg#*=}" ;;
    --name=*)       OLLAMA_NAME="${arg#*=}" ;;
    --epochs=*)     EPOCHS="${arg#*=}" ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAIN_PY="$SCRIPT_DIR/Meta model pattern detector/scripts/train_unsloth_llama3.py"
VENV_DIR="$SCRIPT_DIR/.venv-unsloth"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "\n${CYAN}==> $1${NC}"; }
ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; exit 1; }

# ── Check Python ──────────────────────────────────────────────────────────────
step "Checking prerequisites"
command -v python3 &>/dev/null || command -v python &>/dev/null || fail "Python not found."
PYTHON=$(command -v python3 || command -v python)
PY_VER=$($PYTHON --version 2>&1)
ok "Python: $PY_VER"

# ── Venv setup ────────────────────────────────────────────────────────────────
if [ "$TRAIN_ONLY" = false ]; then
    step "Setting up virtual environment"

    if [ ! -d "$VENV_DIR" ]; then
        echo "  Creating venv at $VENV_DIR ..."
        $PYTHON -m venv "$VENV_DIR"
        ok "Venv created"
    else
        ok "Venv already exists"
    fi

    PYTHON="$VENV_DIR/bin/python"
    PIP="$VENV_DIR/bin/pip"

    step "Installing dependencies (first run: ~10 min)"

    $PIP install --upgrade pip --quiet

    echo "  Installing PyTorch 2.x + CUDA 12.1..."
    $PIP install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet \
        || fail "PyTorch install failed"
    ok "PyTorch installed"

    echo "  Installing Unsloth..."
    $PIP install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" --quiet \
        || $PIP install unsloth --quiet \
        || fail "Unsloth install failed"
    ok "Unsloth installed"

    echo "  Installing training deps..."
    $PIP install \
        "transformers>=4.40" \
        "trl>=0.8.6" \
        "peft>=0.10" \
        "accelerate>=0.29" \
        "bitsandbytes>=0.43" \
        "datasets>=2.18" \
        sentencepiece protobuf --quiet \
        || fail "Dependency install failed"
    ok "All dependencies installed"

else
    if [ -f "$VENV_DIR/bin/python" ]; then
        PYTHON="$VENV_DIR/bin/python"
        ok "Using existing venv"
    else
        ok "Using system Python"
    fi
fi

[ "$SETUP" = true ] && { echo -e "\n${GREEN}[DONE] Setup complete.${NC}"; exit 0; }

# ── Validate dataset ──────────────────────────────────────────────────────────
step "Validating dataset"
[ -f "$DATASET" ] || fail "Dataset not found: $DATASET\n  Pass --dataset=<path>"
LINE_COUNT=$(wc -l < "$DATASET")
ok "Dataset: $DATASET ($LINE_COUNT examples)"

# ── Run training ──────────────────────────────────────────────────────────────
step "Starting fine-tuning"
START=$(date +%s)

ABS_OUTPUT="$SCRIPT_DIR/output/llama3_finetuned"
ABS_GGUF="$SCRIPT_DIR/output/gguf"
mkdir -p "$ABS_OUTPUT" "$ABS_GGUF"

$PYTHON "$TRAIN_PY" \
    --dataset  "$DATASET" \
    --output   "$ABS_OUTPUT" \
    --gguf_dir "$ABS_GGUF" \
    --epochs   "$EPOCHS"

END=$(date +%s)
ELAPSED=$(( END - START ))
ok "Training finished in $(printf '%02d:%02d:%02d' $((ELAPSED/3600)) $((ELAPSED%3600/60)) $((ELAPSED%60)))"

# ── Import into Ollama ────────────────────────────────────────────────────────
if [ "$SKIP_OLLAMA" = false ]; then
    step "Importing into Ollama as '$OLLAMA_NAME'"

    GGUF_FILE=$(find "$ABS_GGUF" -name "*.gguf" 2>/dev/null | head -1)

    if [ -z "$GGUF_FILE" ]; then
        warn "No .gguf found in $ABS_GGUF — skipping Ollama import"
    else
        MODELFILE="$SCRIPT_DIR/Modelfile"
        cat > "$MODELFILE" <<EOF
FROM $GGUF_FILE

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"

SYSTEM """You are a helpful AI assistant created by Saath AI."""
EOF
        echo "  Modelfile: $MODELFILE"
        ollama create "$OLLAMA_NAME" -f "$MODELFILE" \
            && ok "Imported as '$OLLAMA_NAME'" \
            || warn "Ollama import failed. Run: ollama create $OLLAMA_NAME -f $MODELFILE"

        echo -e "\n${GREEN}  Run it: ollama run $OLLAMA_NAME${NC}"
    fi
fi

echo -e "\n${GREEN}[ALL DONE] Full pipeline complete!${NC}"

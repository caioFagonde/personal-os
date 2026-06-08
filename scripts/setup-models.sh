#!/usr/bin/env bash
set -Eeuo pipefail
# setup-models.sh — Interactive setup for model-runtime providers.
# No downloads happen without explicit user consent.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Personal OS — Model Runtime Provider Setup ==="
echo ""
echo "This script helps you install and configure real inference providers"
echo "to replace the demo/heuristic fallbacks."
echo ""
echo "Available providers:"
echo "  [1] tesseract    — OCR (apt/brew install, no model download)"
echo "  [2] paddleocr    — OCR (pip install, ~1.5GB model download)"
echo "  [3] yolov8       — Object detection (pip install, model download)"
echo "  [4] whisper       — Audio transcription (pip install, model download)"
echo "  [5] faster-whisper — Audio transcription (pip install, model download)"
echo "  [6] whisper-cpp   — Audio transcription (binary install, model download)"
echo ""

if [[ "${1:-}" == "--list" ]]; then
  exit 0
fi

if [[ "${1:-}" == "--check" ]]; then
  echo "Checking installed providers..."
  errors=0
  if command -v tesseract &>/dev/null; then
    echo "  tesseract: installed ($(tesseract --version 2>&1 | head -1))"
  else
    echo "  tesseract: not found"
  fi
  python3 -c "import paddleocr" 2>/dev/null && echo "  paddleocr: installed" || echo "  paddleocr: not found"
  python3 -c "import ultralytics" 2>/dev/null && echo "  yolov8 (ultralytics): installed" || echo "  yolov8 (ultralytics): not found"
  python3 -c "import whisper" 2>/dev/null && echo "  whisper: installed" || echo "  whisper: not found"
  python3 -c "import faster_whisper" 2>/dev/null && echo "  faster-whisper: installed" || echo "  faster-whisper: not found"
  if command -v whisper-cpp &>/dev/null || command -v whisper.cpp &>/dev/null; then
    echo "  whisper-cpp: installed"
  else
    echo "  whisper-cpp: not found"
  fi
  exit 0
fi

read -rp "Which provider would you like to set up? [1-6, or q to quit]: " choice

case "${choice}" in
  1)
    echo ""
    echo "Installing tesseract..."
    if command -v apt-get &>/dev/null; then
      echo "  Will run: sudo apt-get install -y tesseract-ocr"
      read -rp "  Proceed? [y/N]: " confirm
      if [[ "$confirm" =~ ^[Yy] ]]; then
        sudo apt-get install -y tesseract-ocr
        echo ""
        echo "Done. Set these in your .env:"
        echo "  OCR_PROVIDER=tesseract"
        echo "  TESSERACT_INSTALLED=true"
        echo "  TESSERACT_CONFIGURED=true"
        echo "  # After verifying: TESSERACT_READY=true"
      else
        echo "Aborted."
      fi
    elif command -v brew &>/dev/null; then
      echo "  Will run: brew install tesseract"
      read -rp "  Proceed? [y/N]: " confirm
      if [[ "$confirm" =~ ^[Yy] ]]; then
        brew install tesseract
        echo ""
        echo "Done. Set these in your .env:"
        echo "  OCR_PROVIDER=tesseract"
        echo "  TESSERACT_INSTALLED=true"
        echo "  TESSERACT_CONFIGURED=true"
        echo "  # After verifying: TESSERACT_READY=true"
      else
        echo "Aborted."
      fi
    else
      echo "  No supported package manager found. Install tesseract manually."
    fi
    ;;
  2)
    echo ""
    echo "WARNING: paddleocr requires ~1.5GB of model downloads."
    read -rp "  Proceed with pip install paddleocr? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy] ]]; then
      pip install paddleocr
      echo ""
      echo "Done. Set these in your .env:"
      echo "  OCR_PROVIDER=paddleocr"
      echo "  PADDLEOCR_INSTALLED=true"
      echo "  PADDLEOCR_CONFIGURED=true"
      echo "  # After verifying: PADDLEOCR_READY=true"
    else
      echo "Aborted — no download performed."
    fi
    ;;
  3)
    echo ""
    echo "WARNING: ultralytics (YOLOv8) will download model weights on first use."
    read -rp "  Proceed with pip install ultralytics? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy] ]]; then
      pip install ultralytics
      echo ""
      echo "Done. Set these in your .env:"
      echo "  VISION_PROVIDER=yolov8"
      echo "  YOLOV8_INSTALLED=true"
      echo "  YOLOV8_CONFIGURED=true"
      echo "  # After verifying: YOLOV8_READY=true"
    else
      echo "Aborted — no download performed."
    fi
    ;;
  4)
    echo ""
    echo "WARNING: openai-whisper requires model downloads (tiny=~75MB, base=~150MB, small=~500MB, medium=~1.5GB, large=~3GB)."
    read -rp "  Proceed with pip install openai-whisper? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy] ]]; then
      pip install openai-whisper
      echo ""
      echo "Done. Set these in your .env:"
      echo "  AUDIO_PROVIDER=whisper"
      echo "  WHISPER_INSTALLED=true"
      echo "  WHISPER_CONFIGURED=true"
      echo "  # After verifying: WHISPER_READY=true"
    else
      echo "Aborted — no download performed."
    fi
    ;;
  5)
    echo ""
    echo "WARNING: faster-whisper requires model downloads."
    read -rp "  Proceed with pip install faster-whisper? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy] ]]; then
      pip install faster-whisper
      echo ""
      echo "Done. Set these in your .env:"
      echo "  AUDIO_PROVIDER=faster-whisper"
      echo "  FASTER-WHISPER_INSTALLED=true"
      echo "  FASTER-WHISPER_CONFIGURED=true"
      echo "  # After verifying: FASTER-WHISPER_READY=true"
    else
      echo "Aborted — no download performed."
    fi
    ;;
  6)
    echo ""
    echo "whisper-cpp must be installed from source or a package manager."
    echo "See: https://github.com/ggerganov/whisper.cpp"
    echo "No automatic download will be performed."
    ;;
  q|Q)
    echo "Exiting."
    ;;
  *)
    echo "Invalid choice."
    exit 1
    ;;
esac

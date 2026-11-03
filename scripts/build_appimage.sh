#!/bin/sh
set -eu

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPIMAGETOOL="${APPIMAGETOOL:-appimagetool}"
PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"
VARIANT="${1:-normal}"

case "$VARIANT" in
    normal)
        SPEC_FILE="llm_evaluator.spec"
        BUNDLE_NAME="LlmEvaluator"
        DISPLAY_NAME="Project Harbor Benchmark"
        PREFETCH_MODEL=1
        ;;
    demo)
        SPEC_FILE="llm_evaluator_demo.spec"
        BUNDLE_NAME="LlmEvaluatorDemo"
        DISPLAY_NAME="Project Harbor Benchmark (Demo)"
        PREFETCH_MODEL=0
        ;;
    *)
        echo "Uso: $0 [normal|demo]" >&2
        exit 1
        ;;
esac

APP_DIR="$PROJECT_ROOT/build/AppDir-$VARIANT"
OUTPUT_FILE="$PROJECT_ROOT/dist/$BUNDLE_NAME-x86_64.AppImage"

cd "$PROJECT_ROOT"

if [ "$PREFETCH_MODEL" = "1" ]; then
    "$PYTHON" scripts/prefetch_model.py
fi
"$PYTHON" -m PyInstaller --noconfirm "$SPEC_FILE"

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/usr/lib"
cp -r "dist/$BUNDLE_NAME" "$APP_DIR/usr/lib/$BUNDLE_NAME"
sed "s/LlmEvaluator/$BUNDLE_NAME/g" packaging/linux/AppRun > "$APP_DIR/AppRun"
sed -e "s/LlmEvaluator/$BUNDLE_NAME/g" -e "s/^Name=.*/Name=$DISPLAY_NAME/" \
    packaging/linux/llm-evaluator.desktop > "$APP_DIR/llm-evaluator.desktop"
cp packaging/linux/llm-evaluator.png "$APP_DIR/llm-evaluator.png"
chmod +x "$APP_DIR/AppRun"

ARCH=x86_64 "$APPIMAGETOOL" "$APP_DIR" "$OUTPUT_FILE"
echo "AppImage gerado em $OUTPUT_FILE"

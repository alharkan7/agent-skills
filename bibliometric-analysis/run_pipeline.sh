#!/usr/bin/env bash
# run_pipeline.sh
# End-to-end bibliometric analysis script

# Help message
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Usage: ./run_pipeline.sh [OPTIONS] -- [KEYWORDS]"
    echo ""
    echo "Options:"
    echo "  --skip-filtering    Skip the Indonesia-specific relevance filtering."
    echo ""
    echo "Environment:"
    echo "  OPENALEX_EMAIL      Contact email for the OpenAlex polite pool (optional)."
    echo ""
    echo "Example:"
    echo "  ./run_pipeline.sh --skip-filtering -- \"'machine learning'\" \"'deep learning'\""
    echo "  ./run_pipeline.sh -- \"'digital activism'\""
    exit 0
fi

SKIP_FILTERING=""
if [ "$1" == "--skip-filtering" ]; then
    SKIP_FILTERING="--skip-filtering"
    shift
fi

# Ensure we skip "--" if passed
if [ "$1" == "--" ]; then
    shift
fi

KEYWORDS=("$@")

# Optional OpenAlex polite-pool email passthrough
EMAIL_ARGS=()
if [ -n "$OPENALEX_EMAIL" ]; then
    EMAIL_ARGS=(--email "$OPENALEX_EMAIL")
fi

echo "=========================================="
echo "Starting Bibliometric Analysis Pipeline..."
echo "=========================================="

# Move to the directory containing this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Generate output directory name based on timestamp and keywords
TS=$(date +%Y%m%d_%H%M)
if [ ${#KEYWORDS[@]} -eq 0 ]; then
    OUT_NAME="${TS}_default_queries"
else
    # Remove quotes, keep alphanumeric, replace spaces with underscores
    KW_CLEAN=$(echo "${KEYWORDS[@]}" | sed "s/['\"]//g" | tr -cd '[:alnum:] ' | tr -s ' ' | tr ' ' '_')
    OUT_NAME="${TS}_${KW_CLEAN}"
fi

# Run directory lives under the invoking directory, not inside the skill install
OUT_DIR="$PWD/reports/$OUT_NAME"
mkdir -p "$OUT_DIR"

echo "Output Directory: $OUT_DIR"
echo ""

cd "$DIR/scripts"

if [ ${#KEYWORDS[@]} -eq 0 ]; then
    echo "Running with default queries..."
    if [ -n "$SKIP_FILTERING" ]; then
        python3 fetch_bibliometric_data.py --skip-filtering "${EMAIL_ARGS[@]}" --out-dir "$OUT_DIR"
    else
        python3 fetch_bibliometric_data.py "${EMAIL_ARGS[@]}" --out-dir "$OUT_DIR"
    fi
else
    echo "Running with custom keywords: ${KEYWORDS[@]}"
    if [ -n "$SKIP_FILTERING" ]; then
        python3 fetch_bibliometric_data.py --skip-filtering "${EMAIL_ARGS[@]}" --out-dir "$OUT_DIR" --keywords "${KEYWORDS[@]}"
    else
        python3 fetch_bibliometric_data.py "${EMAIL_ARGS[@]}" --out-dir "$OUT_DIR" --keywords "${KEYWORDS[@]}"
    fi
fi

if [ $? -ne 0 ]; then
    echo "Error fetching data. Exiting."
    exit 1
fi

echo ""
echo "Running auto-screen data..."
if [ -n "$SKIP_FILTERING" ]; then
    python3 auto_screen_data.py --skip-filtering --out-dir "$OUT_DIR"
else
    python3 auto_screen_data.py --out-dir "$OUT_DIR"
fi

if [ $? -ne 0 ]; then
    echo "Error screening data. Exiting."
    exit 1
fi

echo ""
echo "Extracting insights..."
python3 extract_insights.py --out-dir "$OUT_DIR"
if [ $? -ne 0 ]; then
    echo "Error extracting insights. Exiting."
    exit 1
fi

echo ""
echo "Generating visualizations..."
python3 visualize_bibliometric.py --out-dir "$OUT_DIR"
if [ $? -ne 0 ]; then
    echo "Error generating visualizations. Exiting."
    exit 1
fi

echo ""
echo "=========================================="
echo "Pipeline completed successfully!"
echo "All files saved to: $OUT_DIR"
echo "=========================================="

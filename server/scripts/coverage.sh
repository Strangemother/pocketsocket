#!/usr/bin/env bash

set -Eeuo pipefail

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COVERAGE_DIR="$SERVER_DIR/../results/coverage/nim"
NIMCACHE_DIR="$COVERAGE_DIR/nimcache"
REPORT_SOURCE="$COVERAGE_DIR/lcov.info"
TEST_TARGET_DIR="$SERVER_DIR/.coco-tests"
LCOV_WRAPPER_DIR="$(mktemp -d)"

cd "$SERVER_DIR"

for command in coco lcov genhtml; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "error: '$command' is required to run Nim coverage" >&2
        if [[ "$command" == "coco" ]]; then
            echo "Install it with: nimble install https://github.com/binhonglee/coco.git" >&2
        elif [[ "$command" == "lcov" || "$command" == "genhtml" ]]; then
            echo "Install LCOV with: sudo apt-get install lcov" >&2
        fi
        exit 1
    fi
done

rm -rf "$COVERAGE_DIR"
mkdir -p "$COVERAGE_DIR"
rm -rf "$TEST_TARGET_DIR"
mkdir -p "$TEST_TARGET_DIR"
cp tests/*.nim "$TEST_TARGET_DIR/"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    'exec /usr/bin/lcov --ignore-errors mismatch "$@"' \
    > "$LCOV_WRAPPER_DIR/lcov"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    'exec /usr/bin/genhtml --ignore-errors unmapped "$@"' \
    > "$LCOV_WRAPPER_DIR/genhtml"
chmod +x "$LCOV_WRAPPER_DIR/lcov"
chmod +x "$LCOV_WRAPPER_DIR/genhtml"
export PATH="$LCOV_WRAPPER_DIR:$PATH"
trap 'rm -rf "$TEST_TARGET_DIR" "$LCOV_WRAPPER_DIR"' EXIT

echo "Running coco Nim coverage..."
coco \
    --target ".coco-tests/*.nim" \
    --cov "!.coco-tests" \
    --nimcache "$NIMCACHE_DIR" \
    --report_source "$REPORT_SOURCE" \
    --report_path "$COVERAGE_DIR" \
    --compiler="--hints:off --path:src"

echo "Nim coverage complete: $COVERAGE_DIR/index.html"
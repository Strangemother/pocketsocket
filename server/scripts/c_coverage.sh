#!/usr/bin/env bash

set -Eeuo pipefail

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COVERAGE_DIR="$SERVER_DIR/c_coverage"

cd "$SERVER_DIR"

for command in nimble gcov gcovr; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "error: '$command' is required to run C coverage" >&2
        if [[ "$command" == "gcovr" ]]; then
            echo "Install it with: python3 -m pip install gcovr" >&2
        fi
        exit 1
    fi
done

rm -rf "$COVERAGE_DIR"
mkdir -p "$COVERAGE_DIR"

nimble clean >/dev/null

echo "Running instrumented Nim tests for C coverage..."
for test_file in tests/*.nim; do
    test_name="$(basename "$test_file" .nim)"
    test_cache="$COVERAGE_DIR/nimcache/$test_name"

    echo "  $test_file"
    nimble c \
        --forceBuild \
        --cc:gcc \
        --nimcache:"$test_cache" \
        --out:"$test_cache/$test_name" \
        --passC:-fprofile-arcs \
        --passC:-ftest-coverage \
        --passL:-fprofile-arcs \
        "$test_file"
    "$test_cache/$test_name"
done

echo "Writing C coverage reports to $COVERAGE_DIR"
GCOVR_OPTIONS=(
    --root "$SERVER_DIR"
    --filter '.*@ppocketsocketpkg@.*\.nim\.c$'
    --object-directory "$COVERAGE_DIR/nimcache"
    --gcov-ignore-errors source_not_found
)

gcovr "${GCOVR_OPTIONS[@]}" \
    --output "$COVERAGE_DIR/coverage.txt"
gcovr "${GCOVR_OPTIONS[@]}" \
    --xml-pretty --output "$COVERAGE_DIR/coverage.xml"
gcovr "${GCOVR_OPTIONS[@]}" \
    --html-details --output "$COVERAGE_DIR/coverage.html"

echo "C coverage complete: $COVERAGE_DIR/coverage.html"
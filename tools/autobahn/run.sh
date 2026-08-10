#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
SUITE_DIR="$ROOT_DIR/tools/autobahn"
OUTPUT_DIR=${OUTPUT_DIR:-"$SUITE_DIR/reports"}
CONFIG_DIR="$OUTPUT_DIR/config"
PORT=${PORT:-18091}
IMAGE=${AUTOBAHN_IMAGE:-crossbario/autobahn-testsuite:25.10.1}
CONTAINER_NAME=${AUTOBAHN_CONTAINER_NAME:-pocketsocket-autobahn}

mkdir -p "$CONFIG_DIR" "$OUTPUT_DIR"

command -v docker >/dev/null 2>&1 || {
    printf 'Docker is required to run the Autobahn testsuite.\n' >&2
    exit 1
}

sed "s/__PORT__/${PORT}/g" "$SUITE_DIR/fuzzingclient.template.json" \
    > "$CONFIG_DIR/fuzzingclient.json"

cleanup() {
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

printf 'Target: ws://host.docker.internal:%s\n' "$PORT"
printf 'Autobahn image: %s\n' "$IMAGE"
printf 'Reports: %s\n' "$OUTPUT_DIR"

deadline=$((SECONDS + 15))
listening=false
while (( SECONDS < deadline )); do
    if timeout 1 bash -c "</dev/tcp/127.0.0.1/${PORT}" 2>/dev/null; then
        listening=true
        break
    fi
    sleep 0.1
done
if [[ "$listening" != true ]]; then
    printf 'Pocketsocket is not listening on 127.0.0.1:%s. Start it manually before running this suite.\n' "$PORT" >&2
    exit 1
fi

docker run --rm --name "$CONTAINER_NAME" \
    --add-host host.docker.internal:host-gateway \
    -v "$CONFIG_DIR:/config:ro" \
    -v "$OUTPUT_DIR:/reports" \
    "$IMAGE" \
    wstest --mode fuzzingclient --spec /config/fuzzingclient.json
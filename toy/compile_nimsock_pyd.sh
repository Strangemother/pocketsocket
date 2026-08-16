#!/usr/bin/env bash

set -euo pipefail

nimpy_path="$(nimble path nimpy)"
extension_suffix="$(python3 -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))')"

mkdir -p dist

nim c --app:lib \
    --path:"$nimpy_path" \
    --out:"./dist/toy${extension_suffix}" \
    --threads:on \
    --tlsEmulation:off \
    -d:lto \
    --mm:arc \
    -d:useMalloc \
    -d:release \
    --opt:speed \
    -d:strip \
    toy.nim

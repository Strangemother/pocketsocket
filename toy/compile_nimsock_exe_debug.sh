nim c --app:console \
    --out:./dist/toy-cli.exe \
    --threads:on \
    --tlsEmulation:off \
    -d:lto \
    --mm:arc \
    -d:useMalloc \
    --excessiveStackTrace:on \
    --passL:-static imp.nim

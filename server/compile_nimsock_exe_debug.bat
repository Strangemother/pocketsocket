nimble c --app:console ^
    --out:..\dist/pocketsocket-cli.exe ^
    --threads:on ^
    --tlsEmulation:off ^
    -d:lto ^
    --mm:arc ^
    -d:useMalloc ^
    --excessiveStackTrace:on ^
    --passL:-static src/pocketsocket.nim

nim c --app:lib ^
    --out:..\dist/toy.dll ^
    -d:release ^
    --threads:on ^
    --opt:size ^
    --tlsEmulation:off ^
    --passl:"-static -static-libgcc -static-libstdc++" imp.nim

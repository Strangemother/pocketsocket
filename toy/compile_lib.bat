nim c --app:lib ^
    --out:..\dist/lib/imp.dll ^
    -d:release ^
    --threads:on ^
    --opt:size ^
    --tlsEmulation:off ^
    --passl:"-static -static-libgcc -static-libstdc++" src\pocketsocketpkg\imp.nim

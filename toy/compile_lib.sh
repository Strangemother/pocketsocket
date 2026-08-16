nim c --app:lib \
    --out:./dist/toy.so \
    -d:release \
    --threads:on \
    --opt:size \
    --tlsEmulation:off \
    imp.nim

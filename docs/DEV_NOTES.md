# Developer Notes

This page collects build details and lower-level implementation notes that are useful when developing PocketSocket, but are not needed for the quick start.

## Building the Python Extension

Windows:

```bash
nim c --app:lib --out:mymodule.pyd --threads:on --tlsEmulation:off --passL:-static mymodule
```

Linux and other platforms:

```bash
nim c --app:lib --out:mymodule.so --threads:on mymodule
```

The repository build scripts add release, LTO, ARC, and allocator flags for packaged builds.

## Incoming Socket Memory

There is currently a memory cost associated with incoming socket ingress. With `-d:useMalloc`, the observed leak is approximately 4 KB. Without it, the observed leak is approximately 40 KB.

This is related to ongoing Nim memory-management work:

- https://github.com/nim-lang/Nim/issues/24693
- https://github.com/nim-lang/Nim/pull/24701
- https://github.com/nim-lang/Nim/issues/22510

The current partial mitigation is:

```text
--mm:arc
-d:useMalloc
```

## Windows

For dev on windows:

1. Install Nim: https://nim-lang.org/install_windows.html
2. Install gcc (mingw-w64) https://www.msys2.org/
    info: https://code.visualstudio.com/docs/cpp/config-mingw

# Extra modules are required
# nim c --app:lib --out:imp.dll --passl:"-static -static-libgcc -static-libstdc++" src\imp.nim

# {.pragma: rtl, exportc, dynlib, cdecl.}

proc greet*() {.exportc, dynlib, stdcall.} =
  echo "imp module says hello."


# proc load*() {.exportc, dynlib, stdcall.} =
#   echo "imp module says hello."


# proc greet*() {.rtl.} =
#   echo "imp module says hello."
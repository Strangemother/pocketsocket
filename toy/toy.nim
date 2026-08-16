import nimpy

proc greet*() {.exportpy.} =
  echo "imp module says hello."
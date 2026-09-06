# Package
version       = "2.0.9"
author        = "Strangemother"
description   = "websocket server"
license       = "MIT"
srcDir        = "src"
binDir        = "../dist"
installExt    = @["nim"]
namedBin      = {"pocketsocket": "pocketsocket-cli-release"}.toTable

# Dependencies

requires "nim >= 2.0.2"
requires "nimpy"
requires "ws"
requires "docopt"
requires "zippy >= 0.10.9"
requires "webby >= 0.2.1"
requires "crunchy >= 0.1.11"

import std/[os, strutils]

# Temporary suppression for a Nim 2.2 stdlib ProveInit warning instantiated by Mummy.
switch("warning", "ProveInit:off")

task buildDebug, "build debug pocketsocket-cli":
  switch("out", toExe(binDir / "pocketsocket-cli-debug"))
  setCommand "c", srcDir / "pocketsocket.nim"

proc configurePythonExtension() =
  let pythonCommand = getEnv("POCKETSOCKET_PYTHON", "python3")
  var (extSuffix, exitCode) = gorgeEx(pythonCommand, """
import sysconfig
print(sysconfig.get_config_var("EXT_SUFFIX"))
""")
  stripLineEnd(extSuffix)

  if exitCode != 0:
    raise newException(OSError, "Could not get python native extension suffix")

  if extSuffix.endsWith(".pyd"):
    switch("cc", "vcc")
    switch("passC", "/FI\"" & absolutePath(srcDir / "pocketsocket_winsock_compat.h") & "\"")
    if extSuffix.endsWith("-win32.pyd"):
      switch("cpu", "i386")
    elif extSuffix.endsWith("-win_amd64.pyd"):
      switch("cpu", "amd64")
    elif extSuffix.endsWith("-win_arm64.pyd"):
      switch("cpu", "arm64")
    else:
      raise newException(ValueError, "Unsupported Windows extension suffix: " & extSuffix)

  switch("path", srcDir)
  switch("out", ".." / "package" / "pocketsocket_server" & extSuffix)

task buildPyd, "build python extension module":
  configurePythonExtension()
  # `nimble build` injects -d:release, but a custom task does not: without this
  # the extension ships as an unoptimised debug build (measured ~2x slower).
  switch("define", "release")
  setCommand "c", srcDir / "pocketsocketpkg" / "pocketsocket_server.nim"

task buildPydDebug, "build python extension module with debug info":
  configurePythonExtension()
  setCommand "c", srcDir / "pocketsocketpkg" / "pocketsocket_server.nim"

after build:
  let artifact = toExe(binDir / "pocketsocket-cli-release")
  if fileExists(artifact):
    let (size, exitCode) = gorgeEx("stat -c %s " & quoteShell(artifact))
    echo("Produced file: ", artifact)
    if exitCode == 0:
      let sizeKiB = parseInt(size.strip()) / 1024
      echo("File size: ", formatFloat(sizeKiB, ffDecimal, 1), " KiB")

task buildCliCI, "build pocketsocket-cli for CI":
  # For simpler logic in CI, tag binary name with target OS and CPU
  switch("define", "release")
  switch("path", srcDir)
  switch("out", toExe(binDir / "pocketsocket-cli-" & hostOS & "_" & hostCPU))
  setCommand "c", srcDir / "pocketsocket.nim"

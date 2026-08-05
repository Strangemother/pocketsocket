#[
  Python GIL (Global Interpreter Lock) helpers.

  nimpy does not expose the GIL API, and including `Python.h` directly clashes
  with nimpy's `Py_None` wrapper. Instead the symbols are resolved from the
  libpython handle nimpy has already loaded.

  Any Python C-API call made from a mummy worker thread (i.e. every
  `call_py_hook`) must happen while this thread holds the GIL, otherwise
  nimpy's marshalling reads uninitialised thread state and segfaults.
]#

import std/dynlib
import nimpy/py_lib as lib

type
  PyGILState* = distinct cint
  PyThreadStatePtr* = pointer

var
  pyGILStateEnsure: proc(): PyGILState {.cdecl, gcsafe.}
  pyGILStateRelease: proc(state: PyGILState) {.cdecl, gcsafe.}
  pyEvalSaveThread: proc(): PyThreadStatePtr {.cdecl, gcsafe.}
  pyEvalRestoreThread: proc(state: PyThreadStatePtr) {.cdecl, gcsafe.}
  gilProcsLoaded: bool


proc ensure_gil_procs*(): bool {.discardable, gcsafe.} =
  {.gcsafe.}:
    if gilProcsLoaded:
      return not pyGILStateEnsure.isNil
    if lib.pyLib.isNil or lib.pyLib.module.isNil:
      return false
    let m = lib.pyLib.module
    pyGILStateEnsure = cast[typeof(pyGILStateEnsure)](m.symAddr("PyGILState_Ensure"))
    pyGILStateRelease = cast[typeof(pyGILStateRelease)](m.symAddr("PyGILState_Release"))
    pyEvalSaveThread = cast[typeof(pyEvalSaveThread)](m.symAddr("PyEval_SaveThread"))
    pyEvalRestoreThread = cast[typeof(pyEvalRestoreThread)](m.symAddr("PyEval_RestoreThread"))
    gilProcsLoaded = true
    result = not pyGILStateEnsure.isNil


proc acquire_gil*(): PyGILState {.gcsafe.} =
  #[ Attach this (non-python) thread to the interpreter and take the GIL. ]#
  {.gcsafe.}:
    ensure_gil_procs()
    if pyGILStateEnsure.isNil:
      return PyGILState(0)
    result = pyGILStateEnsure()


proc release_gil*(state: PyGILState): void {.gcsafe.} =
  {.gcsafe.}:
    if not pyGILStateRelease.isNil:
      pyGILStateRelease(state)


proc save_thread*(): PyThreadStatePtr {.gcsafe.} =
  #[ Drop the GIL held by the calling python thread, so worker threads can
     acquire it. Must be paired with `restore_thread`. ]#
  {.gcsafe.}:
    ensure_gil_procs()
    if pyEvalSaveThread.isNil:
      return nil
    result = pyEvalSaveThread()


proc restore_thread*(state: PyThreadStatePtr): void {.gcsafe.} =
  {.gcsafe.}:
    if state != nil and not pyEvalRestoreThread.isNil:
      pyEvalRestoreThread(state)

import std/[locks, tables]
import ../mummy

type
  ConnectionContext* = object
    headers*: HttpHeaders
    remoteAddress*: string
    path*: string

var contexts: Table[uint64, ConnectionContext]
var lock: locks.Lock

locks.initLock(lock)


proc registerContext*(uuid: uint64, context: ConnectionContext) =
  {.gcsafe.}:
    withLock lock:
      contexts[uuid] = context


proc hasContext*(uuid: uint64): bool =
  {.gcsafe.}:
    #[ 
      Given a UUID, check if a context is registered for it. 
    ]#
    withLock lock:
      result = contexts.hasKey(uuid)


proc getContext*(uuid: uint64): ConnectionContext =
  {.gcsafe.}:
    withLock lock:
      if contexts.hasKey(uuid):
        result = contexts[uuid]
      else:
        raise newException(ValueError, "No context found for UUID: " & $uuid)


proc removeContext*(uuid: uint64) =
  {.gcsafe.}:
    withLock lock:
      contexts.del(uuid)
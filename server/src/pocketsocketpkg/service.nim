#[
  server lifecycle and the Python-facing surface
]# 
import std/[cpuinfo, locks, monotimes, os, times]
import ../mummy, ../mummy/routers
import submodule
import broadcast
import ingress
import gil
import config

type
  ServerLifecycle = enum
    ServerIdle
    ServerStarting
    ServerRunning
    ServerStopping
    ServerFailed

  ServerThreadArgs = object
    server: Server
    address: string
    port: Port

var
  server: Server
  wake_time: MonoTime = getMonoTime()
  serverThread: Thread[ServerThreadArgs]
  serverThreadStarted = false
  lifecycleLock: Lock
  lifecycleCond: Cond
  lifecycleState = ServerIdle
  startupError = ""
  servingThreadId = 0

# Always remember to init the lock and cond before using them
initLock(lifecycleLock)
initCond(lifecycleCond)


proc send_all*(message_kind: MessageKind, message_data: string, exclude_uuid: uint64): int =
  #[ Send a message to _all_ clients. Provide an exclude for ignoring the
    receiver]#
  # The connected clients are owned by `broadcast`, which registers them as
  # they connect.
  return broadcast.locked_send_all(message_kind, message_data, exclude_uuid)


proc send*(uuid: uint64, message_kind: MessageKind, message_data: string): int =
  #[ Send a message to the target UUID websocket, with the _kind_ being the
     message type, such as 0 for text.

     return int for success - 0 being ok, any other integer representing a
     error code (typically 1)
  ]#
  return broadcast.locked_send(uuid, message_kind, message_data)


proc close_remove_client*(uuid: uint64): void =
  broadcast.locked_close_remove_client(uuid)


proc closeActiveServer() =
  var activeServer: Server
  withLock lifecycleLock:
    activeServer = server
    if activeServer != nil:
      lifecycleState = ServerStopping

  if activeServer != nil:
    activeServer.close()


proc ctrlc() {.noconv.} =
  echo "Ctrl+C fired!"
  closeActiveServer()


proc shutdown_server*(): void =
  echo "nim::shutdown_server"
  closeActiveServer()

  var shouldJoin = false
  withLock lifecycleLock:
    shouldJoin = serverThreadStarted and servingThreadId != getThreadId()

  if shouldJoin:
    joinThread(serverThread)

  withLock lifecycleLock:
    if shouldJoin or not serverThreadStarted:
      server = nil
      serverThreadStarted = false
      servingThreadId = 0
      startupError = ""
      lifecycleState = ServerIdle
      signal(lifecycleCond)


proc poke_wake_time*(): void =
  wake_time = getMonoTime()


proc set_broadcast_mode*(mode:bool): void =
  config.set_broadcast_mode(mode)


proc set_echo_mode*(mode:bool): void =
  config.set_echo_mode(mode)


proc set_print_mode*(mode:bool = false): void =
  config.set_print_mode(mode)

proc set_template_dir*(dir: string): void =
  config.set_template_dir(dir)


proc buildServer(
    worker_threads: int,
    max_message_len: int,
    max_body_len: int,
    tcp_no_delay: bool
  ): Server =
  
  # mummy defaults to countProcessors() * 10 workers, which oversubscribes
  # small hosts badly. 0 keeps that default, anything else is taken literally.
  let workers =
    if worker_threads > 0: worker_threads
    else: max(countProcessors() * 10, 1)

  result = newServer(
      ingress.router,
      websocketHandler = broadcast.websocketHandler_broadcast,
      workerThreads = workers,
      maxMessageLen = max_message_len,
      maxBodyLen = max_body_len,
      tcpNoDelay = tcp_no_delay,
    )

proc prepareServer(address: string, port: int) =
  when isMainModule:
    echo(getWelcomeMessage())

  if config.template_dir.len != 0:
    echo "Using template directory: ", config.template_dir
    submodule.setLoadedTemplate("index.html")

  echo "Serving on http://", address, ":", port
  setControlCHook(ctrlc)


proc run_blocking_server*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void =
  prepareServer(address, port)
  let newServer = buildServer(
    worker_threads,
    max_message_len,
    max_body_len,
    tcp_no_delay,
  )

  withLock lifecycleLock:
    if lifecycleState != ServerIdle:
      raise newException(ValueError, "pocketsocket server is already running")
    server = newServer

  let total_time: Duration = getMonoTime() - wake_time
  echo "TTL: ", $total_time
  # serve() blocks this (python) thread; hand the GIL back so mummy's worker
  # threads are able to acquire it when calling the python hook.
  let threadState = gil.save_thread()
  try:
    server.serve(Port(port), address)
  finally:
    gil.restore_thread(threadState)
  echo "Serve complete"


proc serveThread(args: ServerThreadArgs) {.gcsafe.} =
  withLock lifecycleLock:
    servingThreadId = getThreadId()

  try:
    args.server.serve(args.port, args.address)
    withLock lifecycleLock:
      if lifecycleState == ServerRunning:
        lifecycleState = ServerIdle
      signal(lifecycleCond)
  except Exception as error:
    withLock lifecycleLock:
      {.cast(gcsafe).}:
        startupError = error.msg
      lifecycleState = ServerFailed
      signal(lifecycleCond)


proc run_nonblocking_server*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void =
  prepareServer(address, port)
  let newServer = buildServer(
      worker_threads,
      max_message_len,
      max_body_len,
      tcp_no_delay,
    )
  withLock lifecycleLock:
    if lifecycleState != ServerIdle:
      raise newException(ValueError, "pocketsocket server is already running")
    server = newServer
    startupError = ""
    lifecycleState = ServerStarting
    try:
      createThread(
        serverThread,
        serveThread,
        ServerThreadArgs(
          server: newServer,
          address: address,
          port: Port(port),
        ),
      )
      serverThreadStarted = true
    except Exception:
      server = nil
      serverThreadStarted = false
      lifecycleState = ServerIdle
      startupError = ""
      raise

  let startupDeadline = getMonoTime() + initDuration(seconds = 10)
  var failureMessage = ""
  var startupFailed = false
  while true:
    if newServer.isReady():
      withLock lifecycleLock:
        if lifecycleState == ServerStarting:
          lifecycleState = ServerRunning
          signal(lifecycleCond)
          return
        if lifecycleState == ServerFailed:
          startupFailed = true
          failureMessage = startupError

    if startupFailed:
      break

    withLock lifecycleLock:
      if lifecycleState == ServerFailed:
        startupFailed = true
        failureMessage = startupError

    if startupFailed:
      break

    if getMonoTime() >= startupDeadline:
      startupFailed = true
      failureMessage = "pocketsocket server startup timed out"
      break

    sleep(10)

  var threadWasStarted = false
  withLock lifecycleLock:
    threadWasStarted = serverThreadStarted

  newServer.close()
  if threadWasStarted:
    joinThread(serverThread)

  withLock lifecycleLock:
    server = nil
    serverThreadStarted = false
    servingThreadId = 0
    startupError = ""
    lifecycleState = ServerIdle
    signal(lifecycleCond)

  raise newException(ValueError, failureMessage)


proc run_blocking_server_v1*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void =
  when isMainModule:
    echo(getWelcomeMessage())
  
  if config.template_dir.len != 0:
    echo "Using template directory: ", config.template_dir
    submodule.setLoadedTemplate("index.html")
  # mummy defaults to countProcessors() * 10 workers, which oversubscribes
  # small hosts badly. 0 keeps that default, anything else is taken literally.
  let workers =
    if worker_threads > 0: worker_threads
    else: max(countProcessors() * 10, 1)
  server = newServer(
      ingress.router,
      websocketHandler = broadcast.websocketHandler_broadcast,
      workerThreads = workers,
      maxMessageLen = max_message_len,
      maxBodyLen = max_body_len,
      tcpNoDelay = tcp_no_delay,
    )
  echo "Serving on http://", address, ":", port
  setControlCHook(ctrlc)
  let total_time: Duration = getMonoTime() - wake_time
  echo "TTL: ", $total_time
  # serve() blocks this (python) thread; hand the GIL back so mummy's worker
  # threads are able to acquire it when calling the python hook.
  let threadState = gil.save_thread()
  try:
    server.serve(Port(port), address)
  finally:
    gil.restore_thread(threadState)
  echo "Serve complete"

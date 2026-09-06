include ../src/mummy
import std/unittest

proc maskedFrame(payload: string, opcode: uint8 = 2, finalFrame = true,
                 mask: array[4, uint8] = [0x12'u8, 0xA5, 0x00, 0xFF]): string =
  result.add(char(opcode or (if finalFrame: 0x80'u8 else: 0'u8)))
  if payload.len < 126:
    result.add(char(0x80 or payload.len))
  elif payload.len <= 65535:
    result.add(char(0xFE))
    result.add(char((payload.len shr 8) and 0xFF))
    result.add(char(payload.len and 0xFF))
  else:
    result.add(char(0xFF))
    for shift in countdown(56, 0, 8):
      result.add(char((payload.len.uint64 shr shift) and 0xFF))
  for value in mask:
    result.add(char(value))
  for index, value in payload:
    result.add(char(value.uint8 xor mask[index mod 4]))

proc patternedPayload(length: int): string =
  result = newString(length)
  for index in 0 ..< length:
    result[index] = char(index mod 256)

proc ignoreUpdate(websocket: WebSocket, event: WebSocketEvent, message: Message) =
  discard

suite "receive unmasking":
  var serverStorage: ServerObj
  var activeServer: Server
  var websocket: WebSocket
  var entry: DataEntry

  setup:
    serverStorage = ServerObj()
    activeServer = serverStorage.addr
    activeServer.maxMessageLen = 128 * 1024
    activeServer.websocketHandler = ignoreUpdate
    initLock(activeServer.websocketQueuesLock)
    websocket = WebSocket(server: activeServer, clientSocket: SocketHandle(42), clientId: 1)
    activeServer.websocketQueues[websocket] = initDeque[WebSocketUpdate]()
    activeServer.websocketClaimed[websocket] = true
    entry = DataEntry(kind: ClientSocketEntry, clientId: 1)

  teardown:
    deinitLock(activeServer.websocketQueuesLock)

  test "binary payload boundaries and mask remainders":
    for length in [0, 1, 2, 3, 4, 5, 125, 126, 127, 1024, 16384, 65535, 65536]:
      let payload = patternedPayload(length)
      entry.recvBuf = maskedFrame(payload)
      entry.bytesReceived = entry.recvBuf.len
      check not activeServer.afterRecvWebSocket(websocket.clientSocket, entry)
      require activeServer.websocketQueues[websocket].len == 1
      let update = activeServer.websocketQueues[websocket].popFirst()
      check update.event == MessageEvent
      check update.message.kind == BinaryMessage
      check update.message.data == payload
      check entry.bytesReceived == 0

  test "fragment mask restarts independently of message offset":
    let prefix = "abc"
    entry.recvBuf = maskedFrame(prefix, finalFrame = false)
    entry.bytesReceived = entry.recvBuf.len
    check not activeServer.afterRecvWebSocket(websocket.clientSocket, entry)
    check activeServer.websocketQueues[websocket].len == 0
    check entry.frameState.frameLen == prefix.len
    check entry.frameState.buffer[0 ..< prefix.len] == prefix
    let suffix = patternedPayload(16385)
    entry.recvBuf = maskedFrame(suffix, opcode = 0,
      mask = [0xF1'u8, 0x00, 0x73, 0x21])
    entry.bytesReceived = entry.recvBuf.len
    check not activeServer.afterRecvWebSocket(websocket.clientSocket, entry)
    require activeServer.websocketQueues[websocket].len == 1
    check activeServer.websocketQueues[websocket].popFirst().message.data == prefix & suffix

  test "every split of a short frame retains incomplete input":
    let payload = "split text message"
    let frame = maskedFrame(payload, opcode = 1)
    for split in 1 ..< frame.len:
      entry.recvBuf = frame[0 ..< split]
      entry.bytesReceived = split
      check not activeServer.afterRecvWebSocket(websocket.clientSocket, entry)
      check activeServer.websocketQueues[websocket].len == 0
      check entry.recvBuf == frame[0 ..< split]
      entry.recvBuf.add(frame[split .. ^1])
      entry.bytesReceived = entry.recvBuf.len
      check not activeServer.afterRecvWebSocket(websocket.clientSocket, entry)
      require activeServer.websocketQueues[websocket].len == 1
      let update = activeServer.websocketQueues[websocket].popFirst()
      check update.message.kind == TextMessage
      check update.message.data == payload

  test "coalesced frames preserve a partial following frame":
    let first = maskedFrame("first")
    let payload = patternedPayload(16384)
    let second = maskedFrame(payload)
    entry.recvBuf = first & second[0 ..< 100]
    entry.bytesReceived = entry.recvBuf.len
    check not activeServer.afterRecvWebSocket(websocket.clientSocket, entry)
    require activeServer.websocketQueues[websocket].len == 1
    let firstUpdate = activeServer.websocketQueues[websocket].popFirst()
    check firstUpdate.message.data == "first"
    check entry.bytesReceived == 100
    check entry.recvBuf[0 ..< 100] == second[0 ..< 100]
    entry.recvBuf = entry.recvBuf[0 ..< entry.bytesReceived] & second[100 .. ^1]
    entry.bytesReceived = entry.recvBuf.len
    check not activeServer.afterRecvWebSocket(websocket.clientSocket, entry)
    require activeServer.websocketQueues[websocket].len == 1
    check activeServer.websocketQueues[websocket].popFirst().message.data == payload
    check firstUpdate.message.data == "first"
include ../src/mummy
import std/unittest

suite "outgoing byte accounting":
  test "partial header, body, and next frame preserve offsets":
    let entry = DataEntry(kind: ClientSocketEntry)
    entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "HEAD", buffer2: "body"))
    entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "NEXT", buffer2: "data"))
    check not entry.consumeWritten(2)
    check entry.outgoingBuffers.peekFirst().bytesSent == 2
    check not entry.consumeWritten(3)
    check entry.outgoingBuffers.peekFirst().bytesSent == 5
    check not entry.consumeWritten(5)
    check entry.outgoingBuffers.len == 1
    check entry.outgoingBuffers.peekFirst().bytesSent == 2
    check not entry.consumeWritten(6)
    check entry.outgoingBuffers.len == 0

  test "empty payload and close frame completion":
    let entry = DataEntry(kind: ClientSocketEntry)
    entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "header"))
    entry.outgoingBuffers.addLast(OutgoingBuffer(
      buffer1: "close", isCloseFrame: true, closeConnection: true,
    ))
    check not entry.consumeWritten(10)
    check not entry.closeFrameSent
    check entry.consumeWritten(1)
    check entry.closeFrameSent
    check entry.outgoingBuffers.len == 0

when defined(linux):
  suite "nonblocking output":
    var sockets: array[2, cint]
    var entry: DataEntry

    setup:
      require socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0
      SocketHandle(sockets[0]).setBlocking(false)
      SocketHandle(sockets[1]).setBlocking(false)
      entry = DataEntry(kind: ClientSocketEntry)

    teardown:
      discard posix.close(sockets[0])
      discard posix.close(sockets[1])

    test "gathers headers, empty payloads, and multiple frames in order":
      entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "H1", buffer2: "body1"))
      entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "H2"))
      entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "H3", buffer2: "body3"))
      check not SocketHandle(sockets[0]).drainWrites(entry)
      check entry.outgoingBuffers.len == 0
      var received = newString(100)
      let count = SocketHandle(sockets[1]).recv(received[0].addr, received.len.cint, 0)
      require count > 0
      received.setLen(count)
      check received == "H1body1H2H3body3"

    test "vectored write stops at the close boundary":
      entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "before"))
      entry.outgoingBuffers.addLast(OutgoingBuffer(
        buffer1: "close", isCloseFrame: true, closeConnection: true,
      ))
      entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "never"))
      check SocketHandle(sockets[0]).drainWrites(entry)
      check entry.closeFrameSent
      check entry.outgoingBuffers.len == 1
      var received = newString(100)
      let count = SocketHandle(sockets[1]).recv(received[0].addr, received.len.cint, 0)
      require count > 0
      received.setLen(count)
      check received == "beforeclose"

    test "backpressure retains unsent data and resumes without corruption":
      var bufferSize = 4096.cint
      require setsockopt(SocketHandle(sockets[0]), SOL_SOCKET, SO_SNDBUF,
        bufferSize.addr, sizeof(bufferSize).SockLen) == 0
      var expected = newString(1024 * 1024)
      for index in 0 ..< expected.len:
        expected[index] = char(index mod 251)
      entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "header", buffer2: expected))
      expected = "header" & expected
      check not SocketHandle(sockets[0]).drainWrites(entry)
      require entry.outgoingBuffers.len == 1
      let offset = entry.outgoingBuffers.peekFirst().bytesSent
      check offset > 0
      check offset < maxWriteBytesPerEvent
      check not SocketHandle(sockets[0]).drainWrites(entry)
      check entry.outgoingBuffers.peekFirst().bytesSent == offset
      var received = ""
      var buffer = newString(16384)
      for iteration in 0 ..< 10000:
        let count = SocketHandle(sockets[1]).recv(buffer[0].addr, buffer.len.cint, 0)
        if count > 0:
          received.add(buffer[0 ..< count])
        check not SocketHandle(sockets[0]).drainWrites(entry)
        if received.len == expected.len:
          break
      check received == expected
      check entry.outgoingBuffers.len == 0

    test "short vector budgets resume within the header and body":
      entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "HEAD", buffer2: "payload"))
      entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "NEXT", buffer2: "body"))
      for budget in [2, 4, 7, 6]:
        let written = SocketHandle(sockets[0]).writePending(entry, budget)
        check written == budget
        check not entry.consumeWritten(written)
      check entry.outgoingBuffers.len == 0
      var received = newString(100)
      let count = SocketHandle(sockets[1]).recv(received[0].addr, received.len.cint, 0)
      require count > 0
      received.setLen(count)
      check received == "HEADpayloadNEXTbody"

    test "syscall budget yields with queued frames remaining":
      for index in 0 ..< 300:
        entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "H", buffer2: "B"))
      check not SocketHandle(sockets[0]).drainWrites(entry)
      check entry.outgoingBuffers.len == 300 - maxWriteCallsPerEvent * maxWriteVectors div 2
      var received = newString(1000)
      let count = SocketHandle(sockets[1]).recv(received[0].addr, received.len.cint, 0)
      check count == maxWriteCallsPerEvent * maxWriteVectors

    test "byte budget yields within a large payload":
      var bufferSize = (maxWriteBytesPerEvent * 4).cint
      require setsockopt(SocketHandle(sockets[0]), SOL_SOCKET, SO_SNDBUF,
        bufferSize.addr, sizeof(bufferSize).SockLen) == 0
      entry.outgoingBuffers.addLast(OutgoingBuffer(
        buffer1: "H", buffer2: newString(maxWriteBytesPerEvent * 2),
      ))
      check not SocketHandle(sockets[0]).drainWrites(entry)
      require entry.outgoingBuffers.len == 1
      check entry.outgoingBuffers.peekFirst().bytesSent > 0
      check entry.outgoingBuffers.peekFirst().bytesSent <= maxWriteBytesPerEvent

    test "peer closure is reported without SIGPIPE":
      require posix.shutdown(SocketHandle(sockets[1]), SHUT_RDWR) == 0
      entry.outgoingBuffers.addLast(OutgoingBuffer(buffer1: "header", buffer2: "body"))
      check SocketHandle(sockets[0]).drainWrites(entry)
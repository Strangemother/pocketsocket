import unittest
import pocketsocketpkg/socket_tools
import mummy


suite "socket tools tests":

    test "getWebSocketUUID returns a uint64":
        # Create a dummy WebSocket object for testing
        var dummyWebSocket: WebSocket
        # Call the function
        let uuid = getWebSocketUUID(dummyWebSocket)
        # Check that the result is of type uint64
        check uuid is uint64
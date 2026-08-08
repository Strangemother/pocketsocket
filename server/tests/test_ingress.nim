# Tests for ingress.nim
# Run with: nimble test

import unittest
import mummy

import pocketsocketpkg/ingress
import pocketsocketpkg/connection_context

suite "ingress layer tests":

    test "registerWebSocket registers context":
        let websocket = WebSocket()
        # Allocate the mock request on the shared heap to avoid GC issues.
        # 1. Reserve space for the RequestObj (size of RequestObj)
        # 2. Initialize the allocated memory to zero (allocShared0)
        # 3. Cast the allocated memory to a Request type (cast[Request])
        var mockRequest = cast[Request](allocShared0(sizeof(RequestObj)))
        # Ensure the object is deallocated after the test.
        defer:
            deallocShared(mockRequest)

        # populate the mock request with headers, remoteAddress, and path
        var headers: HttpHeaders
        headers["Upgrade"] = "websocket"
        mockRequest.headers = headers
        mockRequest.remoteAddress = "127.0.0.1"
        mockRequest.path = "/ws/test"

        # Actuate the function under test
        let uuid = ingress.registerWebSocket(mockRequest, websocket)
        
        # test that the context is registered correctly
        let context = connection_context.getContext(uuid)
        check context.headers == mockRequest.headers
        check context.remoteAddress == mockRequest.remoteAddress
        check context.path == mockRequest.path


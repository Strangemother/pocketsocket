# Tests for connection_context.nim
# Run with: nimble test

import unittest
import mummy
import pocketsocketpkg/connection_context

# Set 1000 as a starting UUId, 
# Auto increment for each new test context 
var nextTestUUID = 1000'u64

proc newTestContext(remoteAddress: string): tuple[uuid: uint64, context: ConnectionContext] =
    var headers: HttpHeaders
    headers["Content-Type"] = "application/json"

    result.uuid = nextTestUUID
    result.context = ConnectionContext(
        headers: headers,
        remoteAddress: remoteAddress,
        path: "/test/path"
    )
    inc nextTestUUID

proc contextsMatch(actual: ConnectionContext, expected: ConnectionContext): bool =
    result = actual.headers == expected.headers and
        actual.remoteAddress == expected.remoteAddress and
        actual.path == expected.path

proc checkContext(actual: ConnectionContext, expected: ConnectionContext) =
    check contextsMatch(actual, expected)

suite "connection_context test helpers":

    test "newTestContext generates unique UUIDs":
        let context1 = newTestContext("127.0.0.1")
        let context2 = newTestContext("127.0.0.2")  
        # Check that the UUIDs are unique and incrementing
        check context1.uuid != context2.uuid

    test "contextsMatch correctly validates matching contexts":
        let context1 = newTestContext("127.0.0.1")
        let context1Alt = newTestContext("127.0.0.1")
        let context2 = newTestContext("127.0.0.2")
        let context2Alt = newTestContext("127.0.0.2")

        # Check that checkContext validates matching contexts
        check contextsMatch(context1.context, context1Alt.context)
        check contextsMatch(context2.context, context2Alt.context)
        # Test mismatches without intentionally failing the test.
        check not contextsMatch(context1.context, context2.context)
    

suite "connection_context layer tests":

    test "getContext raises ValueError for non-existent UUID":
        let nonExistentUUID: uint64 = 99999
        var errorMessage = ""

        # Call upon the getContext, expect it to raise a ValueError.
        try:
            discard connection_context.getContext(nonExistentUUID)
        except ValueError as e:
            errorMessage = e.msg

        # If no error raised, the test should fail.
        check errorMessage == "No context found for UUID: " & $nonExistentUUID

    test "getContext return the correct context for a registered UUID":
        let testContext = newTestContext("127.0.0.1")
        let testContext_2 = newTestContext("127.0.0.2")
        
        # Register the contexts for both UUIDs
        connection_context.registerContext(testContext.uuid, testContext.context)
        connection_context.registerContext(testContext_2.uuid, testContext_2.context)

        # Test that the contexts are correctly retrieved 
        let retrievedContext = connection_context.getContext(testContext.uuid)
        checkContext(retrievedContext, testContext.context)

        let retrievedContext_2 = connection_context.getContext(testContext_2.uuid)
        checkContext(retrievedContext_2, testContext_2.context)

    test "registerContext registers context":
        let testContext = newTestContext("127.0.0.1")
        connection_context.registerContext(testContext.uuid, testContext.context)
        let retrievedContext = connection_context.getContext(testContext.uuid)
        checkContext(retrievedContext, testContext.context)
    
    test "hasContext checks context existence":
        let testContext = newTestContext("127.0.0.1")
        connection_context.registerContext(testContext.uuid, testContext.context)

        # Ensure the context is registered
        check connection_context.hasContext(testContext.uuid)
        
        # Remove the context and check again
        connection_context.removeContext(testContext.uuid)
        check not connection_context.hasContext(testContext.uuid)

    test "removeContext removes context":
        let testContext = newTestContext("127.0.0.1")
        connection_context.registerContext(testContext.uuid, testContext.context)

        # Ensure the context is registered
        connection_context.removeContext(testContext.uuid)
        
        # Ensure the context is no longer registered
        check not connection_context.hasContext(testContext.uuid)
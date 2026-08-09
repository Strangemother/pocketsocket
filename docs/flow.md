
# Execution Flow 

The websocket functional flow.

Service runs `service.nim:run_blocking_server`
    Inbound `ingress.nim:router`
    All connections route through `indexHandler`
    Subsequent websocket connections are routed to `broadcast.websocketHandler_broadcast`
Accessor initiates a connection to the websocket server `ingress.nim:indexHandler`
    Upgraded and registered

`broadcast.nim:websocketHandler_broadcast` receives a message 
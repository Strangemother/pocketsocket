"""
Authentication services across websockets.

1. Tokenised client

    A Websocket client can connect with additional header.
    The header should be a unique key for the client.

    This isn't secure as anyone can read the session

    Random token switching on a request changes the allowed client key during
    connection. This ensures a middleman cannot _camp_ on a connection without
    activivity

2. Tier Handoff

    Authenicate on an SSL tier, giving the connecting user an auth key.
    The user connects to the websocket service with the key+secret.

    The "key" and an already known 'secret' are given as an encrypted string

    a. Authenicate a client connection through a seperate service.
    b. Record authenication and provide tier "key"
    c. client connect to websocket with "key+secret"
    d. Succeed: Persist connection; Fail: Drop connection

3. Wrapping

    user has a secret key

    a. A user authenicated for client
        + already knows "secret"
        + receives auth "key"

    b. client sends an encrypted message
        + using "key+secret"
        + contains: message + "new_key"

    c. receiver unpacks the message
        + using "key" and "secret"
        + stores: "new_key"

    d. receiver sends an encrypted message
        + using "new_key+secret"
        + contains: message + "newer_key"

    e. client unpacks the message
        + using: (stored) "new_key" and "secret"
        + stores: "newer_key"

    f. loop (b)


    Like SSH.


"""

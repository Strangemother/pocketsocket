"""Message management and parsing
"""


# Incoming chunked byte data is held in chunks for each client
# until a message is complete.
handling_stacks = {}


def postmaster(message, client, clients):
    '''Respond to a message, managing its flow'''

    # parse the data
    # dispatch to clients
    if message.is_binary:
        return handle_binary(message, client, clients)

    return handle_text(message, client, clients)


def handle_text(message, client, clients):
    '''
    Given a message {data}, store or action upon the expect _text_ content.

    '''

    # Detect switch,
    # encat or continue
    data = message.data
    text = None

    if message.completed:

        if client.id in handling_stacks:
            # If previous bytes exist, stack the last message then create
            # a final byte string.
            handling_stacks[client.id] += (message.data)
            final = bytes()
            for str_bytes in handling_stacks[client.id]:
                final += str_bytes
            # remove the old stack data.
            del handling_stacks[client.id]
            # convert bytes to readable
            text = final.decode('utf-8')
        else:
            text = message.data.decode('utf-8')
    else:
        if client.id not in handling_stacks:
            handling_stacks[client.id] = ()

        handling_stacks[client.id] += (message.data, )


    if text is None:
        return

    return text



def perform_message(text, client, clients, cid=None):
    '''read a text message, handling and dispatching content

    Arguments:
        text {str} -- string data from the client
        client {Client} -- The acting client sending the text message
        clients {dict} -- a dict of all clients connected to this session
    '''
    # convert the text into an expected format
    # react to client plugins
    data = client.session.decode(text, client, clients)
    print('Message', text, data)
    # broadcast(data, client, clients, False, ignore=[client], cid=cid)


def handle_binary(message, client, clients):
    print('Handle binary')
    broadcast(message.data, client, clients, message.is_binary, ignore=[client])


def broadcast(data, client, clients, is_binary=False, ignore=None, cid=None):
    #_man.broadcast(message.data, message.is_binary)
    ignore = ignore or []
    for name in clients:
        if clients[name] in ignore:
            continue
        data = client.session.encode(data, client, clients, is_binary)
        clients[name].send(data, is_binary)

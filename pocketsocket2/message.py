"""Message management and parsing
"""
from urllib.parse import parse_qs
from switch import call_hook


SWITCH = '/'

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


def perform_command(text, client, clients):
    client_msgs = ()
    broadcast_msgs = ()

    data = manage_switched(text, client, clients)

    # Convert the switch command content to user feedback,
    # splitting client and broadcast data
    #
    # This is ugly.
    for key, result in data:
        if result is False:
            print('Key "{}" returned unparsable data'.format(key))
            client.send('Fail: {}'.format(key))
            continue

        _to, *hook_data = result
        if 'CLIENT' in _to:
            client_msgs += ((key, hook_data,), )

        if 'BROADCAST' in _to:
            broadcast_msgs += ((key, hook_data,), )

    for hook_data in client_msgs:
        client.send(str(hook_data))

    for hook_data in broadcast_msgs:
        broadcast(hook_data, client, clients, message.is_binary, ignore=[client])

    return data


def manage_switched(message, client, clients):
    '''A text message starting with a switch value.
    Parse the key property and value, action the switch and return the
    data to broadcast.
    '''
    ignored = []
    res = ()
    # parse using urllib
    ds = parse_qs(message[1:], keep_blank_values=True)
    print('Switched', ds)

    for key in ds:
        if key in ignored:
            continue

        if key.startswith('_'):
            continue

        res += ( (key, call_hook(key, ds, client, clients), ), )
    return res


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
        clients[name].send("{} {}".format(cid or client.id, data), is_binary)

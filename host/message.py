"""Message management and parsing
"""

# Incoming chunked byte data is held in chunks for each client
# until a message is complete.
handling_stacks = {}


class MetaMessage(object):
    '''A class to hold an inbound data value (from a socket) for internal
    managment and session editing. Created in `received_message` given a
    Text or Binary message from the socket, and the attached client.

    A result content to push back to clients is altered by the session and
    any client translators.
    '''
    def __init__(self, message=None, client=None, **content_kwargs):
        self.message = message
        self.client = client
        self._decoded = None
        self.content = ()
        self.content_keys = {'client_id', 'value'}
        self.update(**content_kwargs)


    def copy(self, other=None):
        other = other or self
        """Perform a shallow copy of the current message"""
        msg = MetaMessage(other.message, other.client)
        msg._decoded = other._decoded
        # shallow copy the tuple
        msg.content = other.content + ()
        msg.content_keys = other.content_keys.copy()
        return msg

    def append_content(self, key, value):
        self.content += ( (key, value), )
        self.content_keys.add(key)

    def update(self, **kwargs):
        for k in kwargs:
            self.append_content(k, kwargs[k])

    def append_dict(self, d):
        for k in d:
            self.append_content(k, d[k])

    @property
    def is_binary(self):
        if self.message is None:
            return False
        return self.message.is_binary

    @property
    def is_text(self):
        if self.message is None:
            return True
        return self.message.is_text

    @property
    def data(self):
        return self.message.data

    @property
    def completed(self):
        if self.message is None:
            return True
        return self.message.completed

    @property
    def encoding(self):
        return self.message.encoding

    def __len__(self):
        return len(self.message.__unicode__())

    def __str__(self):
        return self.message.__str__()

    def __unicode__(self):
        return self.message.__unicode__()

    def utf8_decode(self, bytes_str=None):
        if self.message is None:
            return None
        data = bytes_str or self.message.data
        if hasattr(data, 'decode'):
            return data.decode('utf-8')
        return None

    def send(self, *clients):
        rendered = self.render()
        for client in clients:
            msg = self.render(client)
            out = client.session.translate_encode(self, client, None)
            client.send(out)

    def render(self, client=None):
        '''return a complete version of the internal message for
        transport to a client. The internal session, client and translators
        are used for a final string or binary.
        '''
        decoded = self.decode_complete()

        if decoded is None and len(self.content) == 0:
            print('Message is None or not complete.')
            return None

        client = client or self.client
        result = (
            # The value or message content as default
            ('value', decoded, ),
            # The identity of the original client
            ('client_id', client.id if hasattr(client, 'id') else id(client), ),
            )

        # Map in the extra data assigned by plugins.
        # The ordered set is handled later with a translator
        for item in self.content:
            if item[0] in self.content_keys:
                result += ( item, )
            else:
                print('Message rendering does not have content "{}"'.format(item))
        return result

    def decode_complete(self, cache=True):
        '''
        perform a utf8_decode if the internal message is `completed`.
        Return None if the message is not complete.
        '''

        # Detect switch,
        # encat or continue
        data = None
        if self.message is not None:
            data = self.message.data

        client = self.client
        cid = id(client)
        if hasattr(client, 'id'):
            cid = client.id

        text = None
        message = self.message

        if self._decoded is not None and cache is True:
            return self._decoded

        if self.completed:

            if cid in handling_stacks:
                # If previous bytes exist, stack the last message then create
                # a final byte string.
                handling_stacks[cid] += (self.data)
                final = bytes()
                for str_bytes in handling_stacks[cid]:
                    final += str_bytes
                # remove the old stack data.
                del handling_stacks[cid]
                # convert bytes to readable
                text = self.utf8_decode(final)
            else:
                text = self.utf8_decode()
        else:
            if cid not in handling_stacks:
                handling_stacks[cid] = ()

            handling_stacks[client.id] += (self.data, )

        if text is None:
            return

        if cache is True:
            self._decoded = text

        return text



def postmaster(message, client, clients):
    '''Respond to a message, managing its flow'''

    # parse the data
    # dispatch to clients
    if message.is_binary:
        return handle_binary(message, client, clients)

    return message.handle_text(clients)


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

    if isinstance(message, MetaMessage):
        message._decoded = text
        return message

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
        res = client.session.encode(data, client, clients, is_binary)
        clients[name].send(res, is_binary)

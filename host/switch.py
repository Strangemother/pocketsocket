from urllib.parse import parse_qs
from host.digest import PluginBase

METHODS = {}
SWITCH = '/'


class Switch(PluginBase):
    """Action a switch command if the message matches the switch pattern"""

    def text_message(self, message, client):

        success, text = self.extract_default(message, client)
        if success:
            if len(text) > 1 and text[0] == SWITCH:
                data = perform_command(text, client, self.get_clients(client))
                return (True, False)

        return (False, True)


def perform_command(text, client, clients):
    client_msgs = ()
    broadcast_msgs = ()

    data = manage_switched(text, client, clients)

    # Convert the switch command content to user feedback,
    # splitting client and broadcast data
    #
    # This is ugly.
    for key, msg in data:

        if msg is False:
            print('Key "{}" returned unparsable data'.format(key))
            client.send('Fail: {}'.format(key))
            continue

        try:
            msg.send(client)
        except Exception as e:
            print("Error with switch send message", e)
            raise e

    for hook_data in broadcast_msgs:
        for item in hook_data:
            broadcast(item, client, clients, message.is_binary, ignore=[client])

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

    for key in ds:
        if key in ignored:
            continue

        if key.startswith('_'):
            continue

        res += ( (key, call_hook(key, ds, client, clients), ), )
    return res


def autoload_methods(METHODS):
    return dict(
        kick=kick,
        name=name,
        list=names,
        help=list_methods,
        pause=pause,
        info=info,
        )


def add_switch(name, method):
    global METHODS

    METHODS[name] = method


def add_switches(dic):
    global METHODS

    METHODS.update(dic)


def list_methods(value, options, client, clients):
    return METHODS.keys()


def call_hook(key, options, client, clients):
    '''Call an action if it exists within the autoloaded METHODS.
    Return False if the method by key name does not exist.
    '''

    action = METHODS.get(key)

    if action is None:
        print('Method does not exist "switch.{}"'.format(key))
        return False

    return action(options[key], options, client, clients)


def name(value, options, client, clients):
    '''Name a client using the given `value`. returns a tuple, (old, new) name
    and a boolean for success
        ( ('old_name', 'new_name'), True )
    '''
    old_id = client.id
    new_id = value[0]

    if len(new_id) < 2:
        return ( (old_id, new_id,), False, )

    if new_id in clients:
        # override
        client.send('!Cannot change to "{}"'.format(new_id))
        return ( (old_id, new_id,), False, )

    if old_id in clients:
        del clients[old_id]

    client.id = new_id
    clients[new_id] = client

    return ( (old_id, new_id), True, )


# def extend(value, options, client, clients):
def names(value, options, client, clients):
    '''
    Return a list of all client names in `clients`

        ( client.id, ( (name, id), (name, id), ...) )
    '''
    return (client.id, tuple((x, clients[x].id,) for x in clients), )


def pause(value, options, client, clients):
    session = client.session
    import pdb; pdb.set_trace()  # breakpoint 0d4cfd8e //


def info(value, options, client, clients):
    session = client.session
    from channels import master_channels
    d = dict(
            master_channels=master_channels(),
            clients=tuple(session.get_clients().keys()),
        )

    return d


def kick(value, options, client, clients):
    '''
    Send a kick action. Not Complete.
        /name=eric&name=rif
        {'name': ['eric', 'rif']}
        ((True, 'eric'), (False, 'two'))
    '''
    res = ()
    for name in value:
        res += ( (name in clients, name,), )
    return res


METHODS = autoload_methods(METHODS)

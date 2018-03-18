
METHODS = {}

def autoload_methods(METHODS):
    return dict(
        kick=kick,
        name=name,
        list=names,
        channels=set_channels,
        channel=set_channel,
        help=list_methods,
        )


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

    return (('CLIENT',), action(options[key], options, client, clients))


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

def set_channel(value, options, client, clients):
    pass
def set_channels(value, options, client, clients):
    pass

def names(value, options, client, clients):
    '''
    Return a list of all client names in `clients`

        ( client.id, ( (name, id), (name, id), ...) )
    '''
    return (client.id, tuple((x, clients[x].id,) for x in clients), )


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

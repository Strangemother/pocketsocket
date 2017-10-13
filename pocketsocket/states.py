from functools import partial


class States:

    @classmethod
    def keys(cls):
        c = cls
        v =[a for a in dir(c) if not a.startswith('__') and not callable(getattr(c,a))]
        return v

    @classmethod
    def values(cls):
        c = cls
        v =[getattr(c, a) for a in dir(c) if not a.startswith('__') and not callable(getattr(c,a))]
        return v

    @classmethod
    def key_value(cls, value=None, default_value=None):
        '''
        Given a value return its key
        If key is None, a tuple of tuples for every key; (KEY, Value,)
        '''
        c = cls
        v =[(getattr(c, a), a) for a in dir(c) if not a.startswith('__') and not callable(getattr(c,a))]
        dset = dict(v).get(value, default_value)

        return dset


_VALID_STATUS_CODES = [1000, 1001, 1002, 1003, 1007, 1008,
                       1009, 1010, 1011, 3000, 3999, 4000, 4999]


class OPTION_CODE(States):
    '''
    An option code from the client stream

    https://tools.ietf.org/html/rfc6455#page-29
    '''
    STREAM = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


class STATE(States):
    HEADERB1 = 1
    HEADERB2 = 3
    LENGTHSHORT = 4
    LENGTHLONG = 5
    MASK = 6
    PAYLOAD = 7


class StateHandler(object):

    states = None

    _current_state = None

    def get_current_state(self):
        return self._current_state

    def set_current_state(self, v):
        r = v
        if v != self._current_state:
            r = self.state_changed(v)
        self._current_state = r

    def state_changed(self, value):
        ''''''
        print( 'state changed to', value)
        return value

    def call_state(self, *args, **kw):
        '''
        Call the state driven current method with the
        args and kwargs supplied
        '''

        v = kw.get('state', None)
        f = self.resolve_call_state_method(v)
        r = None

        if callable(f):
            r = f(*args, **kw)
        else:
            print( 'No call state function')
        return r

    def resolve_call_state_method(self, state=None):
        a = self.get_call_state_method_name(state)
        if a is not None:
            a = getattr(self, a)
        return a

    def get_call_state_method_name(self, state=None):
        '''
        Return the call state method name, if a state method matching
        the state exists wthin OPTION_CODE

        If no state is given, self.current_state is used. If a method
        for the function exists within self.states map, the name of the
        function is returned.
        '''
        c = state or self.current_state
        name = self.state_method_name(c)

        print( 'checking state', name)

        a = getattr(self, name, None)
        return name if a is not None else None

    def state_method_name(self, state=None):
        '''
        create and return a string for the method name of the
        state. If no state is given, self.current_state is used.
        '''
        c = state or self.current_state
        return '{0}_state'.format(c.lower())

    current_state = property(get_current_state, set_current_state)


class StateManager(object):

    state_class = None
    caller = None
    caller_format = "{0}_state"

    def __init__(self, state=None, caller_format=None, *args, **kwargs):
        self.init_args = args
        self.init_kw = kwargs
        self.caller_format = caller_format or self.caller_format
        self.state_class = kwargs.get('state_class', self.state_class)
        self.caller = kwargs.get('caller', self.caller)
        self._caller = partial(self.caller, self)
        self.set_state(state)
        # super(cls, self).__init__(*args, **kwargs)

    def call(self, *args, **kw):
        # print( "Call StateManager", args)
        if self.caller is None:
            return False
        self._caller(*args, **kw)

        return True

    def set_state(self, state):
        '''
        Given a state value set the state for the next call to the
        StateManger.call
        '''
        # v = States.key_value(self.state_class, state)
        v = self.state_class.key_value(state)
        self._state = v

    def get_state(self):
        return getattr(self.state_class, self._state)

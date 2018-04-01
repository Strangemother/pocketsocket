from pydoc import locate


class PluginBase(object):

    def created(self):
        pass

    def mounted(self, session):
        print('mounted base', self)
        self.session = session

    def add_client(self, client, cid):
        pass

    def remove_client(self, client, cid):
        pass

    def text_message(self, message, client):
        pass

    def binary_message(self, message, client):
        pass

    def decode_message(self, message, client):
        pass

    def encode_message(self, message, client):
        pass

    def broadcast(self, message, client, clients, is_binary, ignore, cid):
        pass

    def extract_default(self, message, client):
        '''return the value of a dict or string
        '''
        if isinstance(message, dict):
            v = message.get('value', None)
            return 'value' in message, v

        if hasattr(message, 'decode_complete'):
            return True, message.decode_complete()

        return True, message


class PluginMixin(object):

    def add_plugins(self, plugins):
        res = {}

        for pls in plugins:
            res[pls] = self.add_plugin(pls, pls)

        return res

    def add_plugin(self, name, plugin_path):
        plugin = locate(plugin_path)

        if plugin is None:
            print('Plugin "{}" does not exist'.format(plugin_path))
            return None

        if callable(plugin):
            plugin = plugin()

        plugin.get_clients = self.get_clients

        if hasattr(plugin, 'created'):
            plugin.created()

        self._plugins[name] = plugin

        if hasattr(plugin, 'mounted'):
            plugin.mounted(self)

        return plugin

    def get_clients(self):
        return self.clients

    def remove_plugin(self, name):
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False

    def get_plugins(self):
        return [x for x in self._plugins.values()]

    def call_plugins(self, name, *a, **kw):
        res = {}
        values = self.get_plugins()
        for p in values:
            func = getattr(p, name)
            if callable(func):
                try:
                    can_continue = func(*a, **kw)
                except TypeError as e:
                    print('error with plugin function:', name, 'of', p)
                    raise e

                used = False
                _continue = True

                if isinstance(can_continue, tuple):
                    used, _continue = can_continue
                elif isinstance(can_continue, bool):
                    used = True
                    _continue = can_continue

                if _continue is False:
                    return False

        return res


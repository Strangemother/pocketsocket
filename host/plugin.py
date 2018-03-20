from pydoc import locate


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
        print('Adding plugin {}'.format(plugin_path))

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
                    print('Break Plugin iteration because', name)
                    return False

        return res


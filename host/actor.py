from host.digest import PluginBase
from pydoc import locate
from threading import Timer, Thread, Event
from datetime import datetime
import argparse


class Actors(PluginBase):
    """Session plugin to provide Actor instances on messages.

    An actor is a programatical client, designed to react to messages
    from a user client.
    Essentially it's the same as an external client, without the websocket
    connection.
    """
    def __init__(self):
        self.actors = {}

    def created(self):
        print('Actors created')

    def close(self):
        for actor in self.actors.values():
            actor.close()

    def mounted(self, session):
        print('mounted base', self)
        self.session = session

        for named in session.settings.ACTORS:
            Act = locate(named)
            if Act is None:
                print('Cannot locate', named)
                continue
            actor = Act()
            actor.created(self)

            self.actors[id(actor)] = actor

        for aid, actor in self.actors.items():
            actor.mounted(session, aid)

    def add_client(self, client, cid):

        for actor in self.actors.values():
            actor.connected(client, cid)

    def remove_client(self, client, cid):

        for actor in self.actors.values():
            actor.disconnected(client, cid)

    def text_message(self, message, client):
        client.send('Actors text_message')

        for actor in self.actors.values():
            actor.text(client, message)

    def binary_message(self, message, client):
        client.send('Actors binary_message')

    def decode_message(self, message, client):
        client.send('Actors decode_message')

    def encode_message(self, message, client):
        client.send('Actors encode_message')

    def broadcast(self, message, client, clients, is_binary, ignore, cid):
        client.send('Actors broadcast')


class Actor(object):
    """An actor can receive and respond to messages in a session."""

    def created(self, plugin):
        """This actor instance is created and initialized for Actors session
        mounting.
        Perform any pre-mounting requirements such as DB connections and
        settings loads.
        """

    def close(self):
        '''
        server has shutdown, kill self.
        '''

    def mounted(self, session, aid):
        """This actor instance has been applied to the given session after `created`
        initialization.
        Perform session integration and perform any first-communications.
        """
        session.actors = self

    def connected(self, client, cid):
        """A Client has connected to the session. The client ID 'cid' may
        be different to the internal client ID."""

    def disconnected(self, client, cid):
        pass

    def released(self):
        """All user clients within the session are disconnected and no live
        connections exist. the Session is 'released' from usage - waiting for
        incoming clients.

        This method may be called more than once for a single session - for each
        occasion the user list is exausted.
        """

    def text(self, client, message):
        pass


class PerpetualTimer(object):

    def __init__(self, t, hFunction):
        self.t = t
        self.hFunction = hFunction
        self.thread = Timer(self.t, self.handle_function)

    def handle_function(self):
        self.hFunction()
        self.thread = Timer(self.t, self.handle_function)
        self.thread.start()

    def start(self):
        self.thread.start()

    def cancel(self):
        self.thread.cancel()


def printer():
    tempo = datetime.today()
    print("{}:{}:{}".format(tempo.hour, tempo.minute, tempo.second))


class ParserMixin(object):

    prefix_chars = ':'

    commands = ()

    def create_parser(self):

        ap = argparse.ArgumentParser(
            argument_default=argparse.SUPPRESS,
            prefix_chars=self.prefix_chars)

        for com in self.commands:
            arg = ":{}".format(com[0])
            ap.add_argument(arg, **com[1])

        return ap

    def parse_line(self, text):
        if hasattr(self, 'parser') is False:
            self.parser = self.create_parser()
        return self.parser.parse_known_args(text.split())

    def text(self, client, message):
        """React upon a text message from the given client.
        The message contains the sent data as utf8 encoded as bytes.

        For every discovered argument, call the corresponding method by arg_[name]
        The optional return from a arg method is appended to an outbound message.
        If any data exists within the result, the 'returned' arg content
        is send back to the originating client.

            :greet hi
                -> Message: "hi"
                <- "I did this"
                -> Message **
        """
        res = {}
        # Split the given message to arg lines.
        # Each line is a seperate call list
        for line in message.utf8_decode().split('\n'):
            namespace, unknown = self.parse_line(line)
            # Iterate over the known arguments, only calling
            # methods for given args.
            for key in dict(namespace._get_kwargs()):

                mn = 'arg_{}'.format(key)
                if hasattr(self, mn) is False:
                    continue

                # arg_greet
                meth = getattr(self, mn)
                value = getattr(namespace, key)
                val = meth(client, message, value, namespace)

                if val is not None:
                    res[key] = val

        # Optionally send back to the client any return data from the methods.
        if len(res) > 0:
            message.update(**res)
            message.send(client)


class Greet(ParserMixin, Actor):
    """An example reacting Actor with Parser mixin.
    Sending ":greet XXX" as text enacts a response text message of "Hi" and
    returns "I did this" from the arg_greet call.

    """
    commands = (
        ('greet', {},),
    )

    def arg_greet(self, client, message, value, namespace):
        """Handle the command starting ith ":greet XXX", given XXX as the
        value.
        """
        message.append_content('value', '{} back.'.format(value))
        message.send(client)
        return 'I did this!'

from host.channels import set_channel


class Clock(Actor):
    """An example threaded timer, constantly ticking the text time to
    all clients in the attached session.

        -> Message: "tick 2018-04-09 21:38:37.454603"

    This is actually _really_ annoying. and should be confined to a channel.
    ... such as "time".
    """

    # Delay in seconds per tick cycle.
    sec_delay = 1

    def created(self, plugin):
        self.channels = None
        self.id = 'clock'

    def mounted(self, session, aid):
        #set_channel(['clock'], {}, self, None)
        self.timer = PerpetualTimer(self.sec_delay, self.tick)
        self.timer.start()
        self.session = session

    def close(self):
        print("Kill clock")
        self.timer.cancel()
        del self.timer

    def tick(self):
        clients = self.session.channels.get_clients(self.id)
        #print('..To clients:', self.id, clients)
        if clients:
            for client in clients:
                client.send('tick {}'.format(datetime.now()))


class ClockResponse(ParserMixin, Actor):
    """An example threaded timer, constantly ticking the text time to
    all clients in the attached session.

        -> Message: "tick 2018-04-09 21:38:37.454603"

    This is actually _really_ annoying. and should be confined to a channel.
    ... such as "time".
    """
    commands = (
        ('time', { "action": 'store_true'},),
    )

    def arg_time(self, client, message, value, namespace):
        return 'tick {}'.format(datetime.now())


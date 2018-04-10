WS_HOST = '0.0.0.0'
WS_PORT = 8008

SESSION_PLUGINS = (
    'host.digest.Announce',
    'host.digest.Mount',
    'host.switch.Switch',
    'host.digest.DirectMessage',
    'host.channels.Channels',
    'host.digest.Broadcast',
    'host.peer.UDP',
    'host.actor.Actors',
)


SESSION_TRANSLATORS = (
        ('timestamp', 'host.session.TimestampEncoder', {},),
        ('json', 'host.session.JSONEncoderDecoder', {},),
        # ('raw', 'host.session.RawEncoder', {},),
    )


UDP_ANNOUNCE = ('localhost', 50000)

ACTORS = (
    'host.actor.Actor',
    'host.actor.Clock',
    'host.actor.ClockResponse',
    'host.actor.Greet',
)

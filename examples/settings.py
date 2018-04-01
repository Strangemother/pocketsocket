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
)


SESSION_TRANSLATORS = (
        ('timestamp', 'host.session.TimestampEncoder', {},),
        ('json', 'host.session.JSONEncoderDecoder', {},),
    )

UDP_ANNOUNCE = ('localhost', 50000)

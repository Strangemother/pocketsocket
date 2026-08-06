import pocketsocket_server


def connected():
    pass

def text_message():
    pass

def binary_message():
    pass

def close():
    pass


def ingress(uuid, etype, event):
    type_map = {
        0: connected,
        1: text_message,
        2: binary_message,
        3: close,
    }

def start(ip='127.0.0.1', port=8001):
    # Add a function or method to run.
    pocketsocket.hook(ingress)
    # start the server
    pocketsocket.run_blocking_server(ip, port)
import uuid
import atexit
from logger import log
from datetime import datetime
from multiprocessing import Process
import multiprocessing
from service import Service
import time


flag = True


def stop_handle(handle):
    '''
    Provide a handle to perform a correct close of its internal process
    '''
    if handle.client:
        handle.client.close()

    return handle.stop()


def close_process(handle):
    _serve = handle.options.serve if handle.options is not None else False
    if _serve is False:
        log('shutdown')
        return stop_handle(handle)
    return cli_loop(handle)


def cli_loop(handle):
    c = 0
    cc = 0
    log('Serving Press Ctrl+C to stop')
    global flag
    while flag:
        try:
            c += 1
            if c == 100000000:
                cc += 1
                c = 0
                log('Serving forever...', cc, datetime.now())
        except KeyboardInterrupt:
            log('Stop server')
            # flag = False
            break

    stopped = stop_handle(handle)
    log('stop handle', stopped)


def process_start_service(condition, queue, *args, **kw):
    '''
    Start the WebSocket service within the context of a pool process.
    '''
    proc_name = multiprocessing.current_process().name
    log('Process Service:', proc_name)

    # service = ServiceWithCondition()
    service = Service()
    service.config = kw.get('config')
    service.name = proc_name
    service.condition = condition
    service.queue = queue
    service.run(*args, **kw)


class WebSocketHandle(object):
    '''
    Class to assist in handling a multiprocess callback
    '''
    # filled by the processor handler on first entry.
    data = None
    client = None

    def __init__(self, options, *args, **kw):
        self.queue = multiprocessing.Queue()
        self.condition = multiprocessing.Condition()
        self.options = options
        self.args = args
        self.kw = kw
        self.uuid = uuid.uuid4

    def boot_wait(self, condition=None, queue=None, *args, **kw):

        self.boot(condition, queue, *args, **kw)
        self.wait()

    def boot(self, condition=None, queue=None, *args, **kw):
        '''
        Start the process using provided or inherited arguments
        '''
        condition = condition or self.condition
        queue = queue or self.queue

        if len(args) == 0:
            args = self.args
        kw.update(self.kw)

        p = Process(name='service',
                    target=process_start_service,
                    args=(condition, queue, args),
                    kwargs=kw,
                )
        p.start()
        self.process = p
        self.close_wait()
        self.send_entry_request()
        self.client = self.make_client()
        return p

    def close_wait(self):
        atexit.register(close_process, self)

        with self.condition:
            log('Waiting for service boot...')
            self.condition.wait()
            self.data = self.get()
        log('Close wait.')

    def send_entry_request(self):
        '''Send a message through the pipe to note incoming request.
        The socket should wait for an exceptance command before attempting
        request. Any early requests will fail.'''
        if self.data is None:
            log('Cannot perform request; data is not applied.')
            return False

        v = dict(
                name='handle',
                uuid=self.data['uuid'],
                request_id=self.uuid,
                command='super'
            )
        log(self.__class__.__name__, 'sending request...')
        self.put(v)
        log('Service booted: {ip}:{port}'.format(**self.data))

    def make_client(self):
        try:
            from websocket import create_connection
        except ImportError as e:
            s = 'Warning: Could not import client module: {}.\n' \
            '-- try: pip install websocket-client'.format(e)
            log(s)
            return None

        a = "ws://{}:{}/".format(self.data['ip'], self.data['port'])
        ws = create_connection(a)
        log('client test...')

        ws.send("Hi.")
        log('sent client welcome message')

        # Print response.
        result = ws.recv()
        log('Receive', result)
        # ws.close()
        return ws

    def close(self):
        'close the client and the server'
        if self.client is not None:
            self.client.close()
        return close_process(self)

    def wait(self):
        return cli_loop(self)

    def join(self):
        return self.process.join()

    def get(self):
        if self.queue.empty() is False:
            return self.queue.get_nowait()
        return None

    def put(self, v):
        return self.queue.put(v)

    def stop(self):
        self.process.terminate()
        time.sleep(.1)
        return self.process.is_alive() == False
        # super(cls, self).__init__(*args, **kwargs)

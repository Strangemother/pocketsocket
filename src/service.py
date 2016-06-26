'''
Main service to maintain and present a server.
'''

from logger import log
from services import *
from clients import *
from pydoc import locate

import multiprocessing
import time
import inspect

import sys

# Public
class Service(WebSocketService):
    '''
    Com allows communication through the pool pipe,
    messages should be met by some basic auth for
    commands of which are RPC like.
    WebSocketServer with communicator and configurations through
    base path import and load.
    '''

    client_handler = JSONClient
    server_handler = SimpleWebSocketServer

    condition = None
    condition_met = False

    def served(self):
        '''
        Iterate the pool put (non blocking) and parse commands
        from the pipe
        '''

        if self.condition_met is True:
            return True

        data = self.getq()
        self.notify_condition()


        if data is not None:
            log('Service command through pipe')
            print 'service data'

        return super(Service, self).served()

    def notify_condition(self):
        '''
        Send through the pipe all new connection data and meet condition.
        '''
        time.sleep(.1)
        # Push back through the pipe for the part to store before run
        data = {
            'name': self.name,
            'ip': self.server_ip,
            'port': self.server_port,
            'uuid': self.uuid,
        }

        if self.queue is None:
            log('queue failure')
        else:
            log('Notifying')
        self.queue.put_nowait(data)

        # Notify any waiting conditions if they exist.
        if self.condition is not None:
            with self.condition:
                log(self.__class__.__name__, 'notify_all')
                self.condition.notify_all()
        # Flag to not perform this task again.
        self.condition_met = True

    def getq(self):
        if self.queue.empty() is False:
            log(self.__class__.__name__, 'get queue')
            return self.queue.get_nowait()
        return None

    def load_config(self, m):
        '''Load a config module and implement def'''
        print 'load', m
        _m = __import__(m)

        lc = locate(_m.CLIENT)
        lh = locate(_m.SERVER)

        if lc is None:
            log('-x Could not load', _m.CLIENT)
        if lh is None:
            log('-x Could not load', _m.SERVER)

        self.client_handler = lc or self.client_handler
        self.server_handler = locate(_m.SERVER) or self.server_handler

    def run(self, ip=None, port=None, cb=None):
        m = 'config'
        self.load_config(m)
        return super(Service, self).run(ip=ip, port=port, cb=cb)


try:
    import watcher
    from watchdog.observers import Observer
    from watchdog.events import LoggingEventHandler


except:
    watcher = None

class ServiceWithFileWatch(Service):

    def get_folder_paths(self):
        # client
        # service
        # this
        # Any file in local module.
        # callback file
        _mod = inspect.getmodule(self.__class__)
        ap = os.path.abspath(_mod.__file__)
        fp = os.path.split(ap)[0]
        return os.path.normpath(ap)

    def serve(self, svc, callback=None):
        self.watcher = self.monitor_files()
        global _local_service
        _local_service = self
        return super(ServiceWithFileWatch, self).serve(svc, callback)

    def monitor_files(self):

        fp = self.get_folder_paths()
        # w = self.monitor(files)
        event_handler = LoggingEventHandler()
        observer = Observer()
        fp = 'C:/Users/jay/Documents/android/python/files/projects/Remoter'
        print 'monitor', fp
        observer.schedule(event_handler, fp, recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        return w

    def monitor(self, dir_path, *args, **kw):

        flags = (watcher.FILE_NOTIFY_CHANGE_FILE_NAME |
                 watcher.FILE_NOTIFY_CHANGE_DIR_NAME)

        p = os.path.normpath(dir_path)
        print p
        '''
        def cb(t, p):
            print 'tr',t,p

        w = watcher.Watcher('C:\\Users\\jay\\Documents\\android\\python\\files\\projects\\Remoter', cb)
        '''
        p = ' C:\\Users\\jay\\Documents\\android\\python\\files\\projects\\Remoter'
        w = watcher.Watcher(p, file_change)
        w.flags = flags
        log('monitor', p)
        w.start()
        return w

    def get_dirs_set(self, files):
        '''Return a list of unique folders from the given files list'''
        print 'create dirs'
        return files


def file_change(change_int, file_name):
    log('File change', file_name)
    # _local_service['service'].terminate()
    # print 'xhange'

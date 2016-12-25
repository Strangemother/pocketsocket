import sys


VER = sys.version_info[0]
if VER >= 3:
    import socketserver
    from http.server import BaseHTTPRequestHandler
    from io import StringIO, BytesIO
else:
    import SocketServer
    from BaseHTTPServer import BaseHTTPRequestHandler
    from StringIO import StringIO


class HTTPRequest(BaseHTTPRequestHandler):

    def __init__(self, request_text):
        if VER >= 3:
            self.rfile = BytesIO(request_text)
        else:
            self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

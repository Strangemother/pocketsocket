# qpy:console
"""
This is a sample for qpython webapp
"""
from logger import log
from optparse import OptionParser
from handle import WebSocketHandle


parser = OptionParser()
parser.add_option("-f", "--file", dest="filename",
                  help="write report to FILE", metavar="FILE")
parser.add_option("-q", "--quiet",
                  action="store_false", dest="verbose", default=True,
                  help="don't print status messages to stdout")
parser.add_option("-i", "--serve",
                  action="store_true", dest="serve", default=False,
                  help="run the service until system interupt.")
parser.add_option("-c", "--config", dest="config",
                  help="Provide a config path")

parsed = parser.parse_args()


def process_run(options=None, *args, **kw):

    h = WebSocketHandle(options, *args, **kw)
    h.boot()
    return h


def main(options, args):
    log('Create service')
    global pr
    pr = process_run(options)


if __name__ == '__main__':
    main(*parsed)

# client gen pu pv
#   give client pu (not through socket)

# Client gen pu pv
#   envrypt with pv

# Server receive enc message
#   decode with public

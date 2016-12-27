from optparse import OptionParser


parser = OptionParser()
parser.add_option("-q", "--quiet",
                  action="store_false",
                  dest="verbose",
                  default=True,
                  help="don't print status messages to stdout")
parser.add_option("-s", "--settings",
                  dest="settings",
                  help="Provide a settings path")
parser.add_option("-p", "--port",
                  type='int',
                  dest="port",
                  help="Provide a port")
parser.add_option("-r", "--ports",
                  dest="ports",
                  help="Provide many ports comma delim")
parser.add_option("-a", "--host",
                  dest="host",
                  help="Provide a host")
parser.add_option("-b", "--hosts",
                  dest="hosts",
                  help="Provide many hosts comma delim")

parsed = parser.parse_args()


import socket
import base64, hashlib, random

def get_local_ip(endpoint='8.8.8.8'):
	'''
	Get the local socket definition, serving the local IP 
	by using the socket getsockname and returning the IP 
	'''
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect((endpoint,80))
	v = s.getsockname()[0]
	s.close()

	return v

def key_generator():
	return base64.b64encode(
		hashlib.sha256( 
			str(
				random.getrandbits(256)) 
			).digest(), 
		random.choice(
			['rA','aZ','gQ','hH','hG','aR','DD']
			)
		).rstrip('==')
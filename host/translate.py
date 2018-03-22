from digest import PluginBase
import json

from datetime import date, datetime

def JSONSerializer(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

class JSONEncoderDecoder(PluginBase):

    ensure_json_out = True

    def decode_message(self, message, client):

        data = message

        if hasattr(message, 'utf8_decode'):
            data = message.utf8_decode()

        try:
            print('Decoding')
            return True, json.loads(data)
        except json.decoder.JSONDecodeError:
            print('  Decoding JSON Failed')
            return False, message

    def encode_message(self, message, client):

        if isinstance(message, dict):

            print('Encoding', type(message))
            message['from'] = client.id
            return True, json.dumps(message, default=JSONSerializer)


        if hasattr(message, 'render'):
            res = message.render()
            data = dict(res)
            jres = json.dumps(data, default=JSONSerializer)
            return True, jres

        if self.ensure_json_out:
            _id = client.id if hasattr(client, 'id') else id(client)
            d = { "from": _id, "value": message }
            v = json.dumps(d, default=JSONSerializer)
            return False, v

        return False, message


from digest import PluginBase
import json

class JSONEncoderDecoder(PluginBase):

    ensure_json_out = True

    def decode_message(self, message, client):

        try:
            print('Decoding')
            return True, json.loads(message)
        except json.decoder.JSONDecodeError:
            print('  Decoding JSON Failed')
            return False, message

    def encode_message(self, message, client):

        if isinstance(message, dict):
            try:
                print('Encoding', type(message))
                message['from'] = client.id
                return True, json.dumps(message)
            except json.decoder.JSONEncodeError:
                print('  Encoding JSON Failed')
        elif self.ensure_json_out:
            d = { "from": client.id, "value": message }
            v = json.dumps(d)
            return False, v

        return False, message


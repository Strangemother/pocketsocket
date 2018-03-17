from message import handle_text
import unittest
from mock import MagicMock, patch, Mock



class TestHandleText(unittest.TestCase):

    def test_handle_text_kick(self):

        msg = Mock()
        msg.data.decode = Mock(return_value='/kick=one&kick=two')
        clients = { 'one': Mock()}
        res = handle_text(msg, Mock(), clients)
        expected = (
            (
                'kick',
                (
                    (True, 'one'),
                    (False, 'two')
                )
            ),
        )

        self.assertEqual(res,  expected)

import unittest

class TestUM(unittest.TestCase):

    def setUp(self):
        pass

    def test_foo(self):
        self.assertEqual(1,2)

if __name__ == '__main__':
    unittest.main()

import unittest
from queens.server import same_origin


class HostingTest(unittest.TestCase):
    def test_local_and_proxy_origins(self):
        self.assertTrue(same_origin('http://127.0.0.1:8000', '127.0.0.1:8000'))
        self.assertTrue(same_origin('https://queens.example', 'queens.example'))
        self.assertFalse(same_origin('https://other.example', 'queens.example'))
        self.assertFalse(same_origin('https://queens.example.other', 'queens.example'))
        self.assertFalse(same_origin('null', 'queens.example'))

import unittest
from app.utils import encode_base62

class TestEncodeBase62(unittest.TestCase):

    def test_encode_base62_default_length(self):
        self.assertEqual(encode_base62(0), '000000')
        self.assertEqual(encode_base62(1), '000001')
        self.assertEqual(encode_base62(61), '00000Z')
        self.assertEqual(encode_base62(62), '000010')
        self.assertEqual(encode_base62(3843), '0000ZZ')

    def test_encode_base62_custom_length(self):
        self.assertEqual(encode_base62(0, 4), '0000')
        self.assertEqual(encode_base62(1, 4), '0001')
        self.assertEqual(encode_base62(61, 4), '000Z')
        self.assertEqual(encode_base62(62, 4), '0010')

if __name__ == '__main__':
    unittest.main()
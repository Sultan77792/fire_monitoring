import unittest
from utils.validators import is_valid_email, is_valid_phone, is_valid_date, is_valid_number

class TestValidators(unittest.TestCase):
    def test_valid_email(self):
        self.assertTrue(is_valid_email("test@example.com"))
        self.assertFalse(is_valid_email("invalid-email"))

    def test_valid_phone(self):
        self.assertTrue(is_valid_phone("+1234567890"))
        self.assertFalse(is_valid_phone("12345"))

    def test_valid_date(self):
        self.assertTrue(is_valid_date("2024-03-10"))
        self.assertFalse(is_valid_date("10-03-2024"))

    def test_valid_number(self):
        self.assertTrue(is_valid_number("123.45"))
        self.assertFalse(is_valid_number("abc"))

if __name__ == "__main__":
    unittest.main()
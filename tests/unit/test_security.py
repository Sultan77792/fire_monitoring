import unittest
from utils.security import hash_password, verify_password, create_jwt, decode_jwt
from datetime import timedelta

class TestSecurity(unittest.TestCase):
    def test_password_hashing(self):
        password = "securepassword"
        hashed_password = hash_password(password)
        self.assertNotEqual(password, hashed_password)
        self.assertTrue(verify_password(password, hashed_password))
        self.assertFalse(verify_password("wrongpassword", hashed_password))

    def test_jwt_token(self):
        token = create_jwt(user_id=1, role="admin", expires_delta=timedelta(minutes=5))
        decoded = decode_jwt(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["user_id"], 1)
        self.assertEqual(decoded["role"], "admin")

if __name__ == "__main__":
    unittest.main()
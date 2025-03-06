import unittest
import os
from utils.logger import log_action, log_error, log_warning

class TestLogger(unittest.TestCase):
    LOG_FILE = "logs/fire_system.log"

    def setUp(self):
        """Удаляет старый лог-файл перед тестами."""
        if os.path.exists(self.LOG_FILE):
            os.remove(self.LOG_FILE)

    def test_log_action(self):
        """Тестирует запись действий в лог."""
        log_action("test_user", "test_action", "Test details")
        with open(self.LOG_FILE, "r") as f:
            logs = f.read()
        self.assertIn("test_user", logs)
        self.assertIn("test_action", logs)
        self.assertIn("Test details", logs)

    def test_log_error(self):
        """Тестирует запись ошибок в лог."""
        log_error("Test error message")
        with open(self.LOG_FILE, "r") as f:
            logs = f.read()
        self.assertIn("ERROR", logs)
        self.assertIn("Test error message", logs)

    def test_log_warning(self):
        """Тестирует запись предупреждений в лог."""
        log_warning("Test warning message")
        with open(self.LOG_FILE, "r") as f:
            logs = f.read()
        self.assertIn("WARNING", logs)
        self.assertIn("Test warning message", logs)

if __name__ == "__main__":
    unittest.main()

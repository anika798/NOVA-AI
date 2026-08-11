"""
Automated Tests for NOVA Error Analyzer Subsystem
"""
import unittest
from nova.project.error_analyzer import ErrorAnalyzer


class TestErrorAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = ErrorAnalyzer()

    def test_classify_module_not_found_error(self):
        stderr = "Traceback (most recent call last):\n  File 'app.py', line 1, in <module>\nModuleNotFoundError: No module named 'fastapi'\n"
        diag = self.analyzer.analyze(stderr=stderr, exit_code=1)

        self.assertEqual(diag["error_type"], "ModuleNotFoundError")
        self.assertEqual(diag["target_package"], "fastapi")
        self.assertTrue(diag["is_recoverable"])

    def test_classify_syntax_error(self):
        stderr = "  File 'main.py', line 5\n    def test(\n             ^\nSyntaxError: unexpected EOF while parsing\n"
        diag = self.analyzer.analyze(stderr=stderr, exit_code=1)

        self.assertEqual(diag["error_type"], "SyntaxError")
        self.assertIn("Syntax", diag["likely_cause"])

    def test_classify_import_error(self):
        stderr = "ImportError: cannot import name 'invalid_symbol' from 'nova'\n"
        diag = self.analyzer.analyze(stderr=stderr, exit_code=1)

        self.assertEqual(diag["error_type"], "ImportError")

    def test_classify_file_not_found_error(self):
        stderr = "FileNotFoundError: [Errno 2] No such file or directory: 'config.json'\n"
        diag = self.analyzer.analyze(stderr=stderr, exit_code=1)

        self.assertEqual(diag["error_type"], "FileNotFoundError")

    def test_classify_type_error(self):
        stderr = "TypeError: unsupported operand type(s) for +: 'int' and 'str'\n"
        diag = self.analyzer.analyze(stderr=stderr, exit_code=1)

        self.assertEqual(diag["error_type"], "TypeError")

    def test_clean_exit(self):
        diag = self.analyzer.analyze(stderr="", stdout="Done", exit_code=0)
        self.assertEqual(diag["error_type"], "None")


if __name__ == "__main__":
    unittest.main()

import io
import pathlib
import sys
import unittest
from contextlib import redirect_stdout


root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "server" / "apis"))

from tools.kicapi import api_fail, api_success


class KicApiTest(unittest.TestCase):
    def test_api_success_shape(self):
        out = io.StringIO()
        with redirect_stdout(out):
            api_success({"ok": 1})
        text = out.getvalue()
        self.assertIn('"allow":1', text)
        self.assertIn('"success":true', text)
        self.assertIn('"data":{"ok": 1}', text)

    def test_api_fail_shape(self):
        out = io.StringIO()
        with redirect_stdout(out):
            api_fail("bad", "Something failed", {"field": "email"})
        text = out.getvalue()
        self.assertIn('"allow":0', text)
        self.assertIn('"success":false', text)
        self.assertIn('"code": "bad"', text)
        self.assertIn('"field": "email"', text)


if __name__ == "__main__":
    unittest.main()

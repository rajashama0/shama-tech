import pathlib
import sys
import unittest


root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "server" / "apis"))

from tools.db_contact_submissions import contact_chk


class ContactValidationTest(unittest.TestCase):
    def valid_input(self):
        return {
            "full_name": "Jane Lead",
            "company_name": "",
            "email": "jane@example.com",
            "phone": "",
            "service_interest": "AI workflow automation",
            "budget_range": "",
            "message": "Please contact me about automation.",
            "source_page": "/contact",
        }

    def test_company_name_is_optional(self):
        res = contact_chk(self.valid_input())
        self.assertEqual(res["status"], 1)
        self.assertEqual(res["obj"]["company_name"], "")

    def test_missing_full_name_fails(self):
        data = self.valid_input()
        data["full_name"] = ""
        res = contact_chk(data)
        self.assertEqual(res["status"], 0)
        self.assertEqual(res["field"], "full_name")

    def test_invalid_email_fails(self):
        data = self.valid_input()
        data["email"] = "not-an-email"
        res = contact_chk(data)
        self.assertEqual(res["status"], 0)
        self.assertEqual(res["field"], "email")

    def test_long_message_fails(self):
        data = self.valid_input()
        data["message"] = "x" * 2001
        res = contact_chk(data)
        self.assertEqual(res["status"], 0)
        self.assertEqual(res["field"], "message")


if __name__ == "__main__":
    unittest.main()

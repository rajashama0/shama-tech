import pathlib
import sys
import unittest


root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "server" / "apis"))

from tools.db_contact_submissions import contact_chk
from tools import db_contact_submissions


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

    def test_contact_add_saves_to_database_helper(self):
        calls = []
        old_insert = db_contact_submissions.insert_to_sql

        def fake_insert(r):
            calls.append(r)
            return {"status": True, "id": 123}

        db_contact_submissions.insert_to_sql = fake_insert

        try:
            res = db_contact_submissions.contact_add(self.valid_input())
        finally:
            db_contact_submissions.insert_to_sql = old_insert

        self.assertEqual(res["status"], 1)
        self.assertEqual(res["id"], 123)
        self.assertIn("obj", res)

        self.assertEqual(res["obj"]["full_name"], "Jane Lead")
        self.assertEqual(res["obj"]["email"], "jane@example.com")
        self.assertEqual(res["obj"]["service_interest"], "AI workflow automation")
        self.assertEqual(res["obj"]["message"], "Please contact me about automation.")
        self.assertEqual(res["obj"]["status"], "new")

        self.assertEqual(calls[0]["table"], "contact_submissions")
        self.assertEqual(calls[0]["set"]["email"], "jane@example.com")
        self.assertEqual(calls[0]["set"]["status"], "new")


if __name__ == "__main__":
    unittest.main()
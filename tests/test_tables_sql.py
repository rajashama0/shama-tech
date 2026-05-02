import pathlib
import unittest


root = pathlib.Path(__file__).resolve().parents[1]
tables_sql = (root / "tables.sql").read_text(encoding="utf-8")


class TablesSqlTest(unittest.TestCase):
    def test_flyton_base_tables_exist(self):
        for table in ["gen", "users", "ses", "logs"]:
            pattern = rf"CREATE TABLE IF NOT EXISTS {table}\s*\("
            self.assertRegex(tables_sql, pattern)

    def test_flyton_base_tables_have_common_fields(self):
        for field in ["name", "is_active", "created_at", "updated_at", "data"]:
            self.assertIn(field, tables_sql)

    def test_contact_submissions_table_exists(self):
        self.assertRegex(tables_sql, r"CREATE TABLE IF NOT EXISTS contact_submissions\s*\(")


if __name__ == "__main__":
    unittest.main()

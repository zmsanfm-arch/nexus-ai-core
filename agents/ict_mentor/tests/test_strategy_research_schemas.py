import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3] / "docs" / "strategy-research" / "schemas"
SCHEMA_FILES = (
    "strategy.schema.json",
    "experiment-plan.schema.json",
    "backtest-result.schema.json",
)


class StrategyResearchSchemaTests(unittest.TestCase):
    def test_all_schemas_are_valid_draft_2020_12(self):
        for filename in SCHEMA_FILES:
            with self.subTest(schema=filename):
                schema = json.loads((ROOT / filename).read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)

    def test_schema_ids_and_titles_are_unique(self):
        schemas = [
            json.loads((ROOT / filename).read_text(encoding="utf-8"))
            for filename in SCHEMA_FILES
        ]
        self.assertEqual(len({schema["$id"] for schema in schemas}), len(schemas))
        self.assertEqual(len({schema["title"] for schema in schemas}), len(schemas))

    def test_schema_documents_parse_as_json(self):
        for filename in SCHEMA_FILES:
            with self.subTest(schema=filename):
                json.loads((ROOT / filename).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

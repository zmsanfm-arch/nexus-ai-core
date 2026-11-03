import json
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

class ICTContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input_validator = Draft202012Validator(json.loads((ROOT / "schemas/input.schema.json").read_text()))
        cls.output_validator = Draft202012Validator(json.loads((ROOT / "schemas/output.schema.json").read_text()))
        cls.examples = json.loads((ROOT / "examples/contract_examples.json").read_text())

    def test_example_inputs(self):
        for name, pair in self.examples.items():
            with self.subTest(example=name):
                self.input_validator.validate(pair["input"])

    def test_example_outputs(self):
        for name, pair in self.examples.items():
            with self.subTest(example=name):
                self.output_validator.validate(pair["output"])

    def test_execution_result_must_be_null(self):
        payload = self.examples["education"]["output"] | {"execution_result": {"status": "submitted"}}
        self.assertTrue(list(self.output_validator.iter_errors(payload)))

    def test_non_advisory_mode_is_rejected(self):
        payload = self.examples["education"]["output"] | {"mode": "autonomous_execution"}
        self.assertTrue(list(self.output_validator.iter_errors(payload)))

    def test_disabled_task_type_is_rejected(self):
        payload = self.examples["education"]["input"] | {"task_type": "ict.autonomous_execution"}
        self.assertTrue(list(self.input_validator.iter_errors(payload)))

    def test_unconfirmed_user_rule_is_rejected(self):
        payload = self.examples["education"]["input"] | {"user_rules": [{"rule_id": "r1", "text": "Risk 1%", "status": "model_assumed"}]}
        self.assertTrue(list(self.input_validator.iter_errors(payload)))

    def test_source_claim_requires_provenance(self):
        payload = self.examples["education"]["output"] | {"source_claims": [{"claim": "ICT says X"}]}
        self.assertTrue(list(self.output_validator.iter_errors(payload)))

if __name__ == "__main__":
    unittest.main()

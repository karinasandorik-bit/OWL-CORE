"""Contract-level tests for OWL Creative Engine. Run: python -m unittest discover -s tests"""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from creative_engine.character_spec import SPEC, assessment, fingerprint

class CharacterDNAContractTests(unittest.TestCase):
    def test_default_passes(self):
        result = assessment(copy.deepcopy(SPEC))
        self.assertTrue(result["accepted"])
        self.assertEqual(result["stage"], "SPEC_VALIDATED")
        self.assertFalse(result["geometry_verified"])
        self.assertFalse(result["mesh_rendered"])
        self.assertFalse(result["device_tested"])

    def test_determinism(self):
        self.assertEqual(fingerprint(SPEC), fingerprint(copy.deepcopy(SPEC)))

    def test_glasses_anatomy_regression(self):
        candidate = copy.deepcopy(SPEC)
        candidate["eyewear"]["temple_route"] = "floating"
        self.assertFalse(assessment(candidate)["accepted"])

    def test_glasses_clearance(self):
        candidate = copy.deepcopy(SPEC)
        candidate["eyewear"]["clearance_mm"] = 1
        self.assertFalse(assessment(candidate)["accepted"])

    def test_missing_wing(self):
        candidate = copy.deepcopy(SPEC)
        candidate["rig"]["bones"].remove("wing_R")
        self.assertFalse(assessment(candidate)["accepted"])

    def test_missing_motion(self):
        candidate = copy.deepcopy(SPEC)
        candidate["rig"]["required_actions"].remove("flight_idle")
        self.assertFalse(assessment(candidate)["accepted"])

    def test_missing_web_target(self):
        candidate = copy.deepcopy(SPEC)
        candidate["targets"].remove("iPhone-Safari-WebGL")
        self.assertFalse(assessment(candidate)["accepted"])

if __name__ == "__main__":
    unittest.main()

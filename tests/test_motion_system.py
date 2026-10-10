"""Regression tests for OWL motion system and design token compilation."""
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from creative_engine.motion_system import TOKENS, STATES, TRANSITIONS, css_variables, manifest, step, validate_tokens

class MotionContractTests(unittest.TestCase):
    def test_all_states_reachable(self):
        reached = {"idle"}
        for _ in range(len(STATES)):
            reached |= {dst for src, edges in TRANSITIONS.items() if src in reached for dst in edges.values()}
        self.assertEqual(reached, set(STATES))

    def test_no_illegal_jump(self):
        with self.assertRaises(ValueError):
            step("resting", "speak")

    def test_full_character_sequence(self):
        state = "idle"
        for event in ("wake", "think", "respond", "finish", "fly", "land"):
            state = step(state, event)
        self.assertEqual(state, "idle")

    def test_token_css(self):
        css = css_variables()
        self.assertIn("--owl-color-accent: #B28EE8;", css)
        self.assertIn("--owl-motion-blink-ms: 160ms;", css)

    def test_reject_invalid_color(self):
        invalid = {**TOKENS, "color": {"accent": "pink"}}
        with self.assertRaises(ValueError):
            validate_tokens(invalid)

    def test_reject_out_of_range_motion(self):
        invalid = {**TOKENS, "motion": {"blink_ms": 0}}
        with self.assertRaises(ValueError):
            validate_tokens(invalid)

    def test_honest_capability_status(self):
        result = manifest()
        self.assertEqual(result["status"], "SPEC_ONLY")
        self.assertFalse(result["rive_connected"])
        self.assertFalse(result["threejs_connected"])

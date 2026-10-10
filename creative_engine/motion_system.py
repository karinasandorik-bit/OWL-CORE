"""OWL creative runtime: semantic design tokens + deterministic animation FSM.

No renderer attached yet. States are declarative, testable, side-effect-free.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass

TOKENS = {
    "color": {"ink": "#171321", "canvas": "#F4F0F7", "accent": "#B28EE8",
              "chrome": "#C7CCD8", "signal": "#D6A6D8"},
    "typography": {"display": "editorial-condensed", "body": "neutral-grotesk"},
    "radius": {"card_px": 16, "control_px": 10},
    "motion": {"blink_ms": 160, "gaze_ms": 280, "attention_ms": 420},
}
STATES = ("idle", "attentive", "thinking", "speaking", "flying", "resting")
TRANSITIONS = {
    "idle": {"wake": "attentive", "sleep": "resting", "fly": "flying"},
    "attentive": {"think": "thinking", "speak": "speaking", "idle": "idle", "fly": "flying"},
    "thinking": {"respond": "speaking", "idle": "idle"},
    "speaking": {"finish": "attentive", "idle": "idle"},
    "flying": {"land": "idle"},
    "resting": {"wake": "idle"},
}

def validate_tokens(tokens=TOKENS):
    colors = tokens.get("color", {})
    if not colors or any(not re.fullmatch(r"#[0-9A-Fa-f]{6}", v) for v in colors.values()):
        raise ValueError("Colors must be 6-digit hex values")
    durations = tokens.get("motion", {})
    if not durations or any(type(v) is not int or not 80 <= v <= 3000 for v in durations.values()):
        raise ValueError("Unsafe motion duration")
    return True

def step(state: str, event: str) -> str:
    if state not in STATES:
        raise ValueError("Unknown state")
    if event not in TRANSITIONS[state]:
        raise ValueError(f"Illegal animation transition: {state} -> {event}")
    return TRANSITIONS[state][event]

def css_variables(tokens=TOKENS) -> str:
    validate_tokens(tokens)
    rows = [f"  --owl-color-{name}: {value};" for name, value in sorted(tokens["color"].items())]
    rows += [f"  --owl-motion-{name.replace('_', '-')}: {value}ms;" for name, value in sorted(tokens["motion"].items())]
    return ":root {\n" + "\n".join(rows) + "\n}"

def manifest() -> dict:
    validate_tokens()
    return {"version": "owl.motion.v1", "states": STATES, "transitions": TRANSITIONS, "tokens": TOKENS,
            "status": "SPEC_ONLY", "rive_connected": False, "threejs_connected": False}

if __name__ == "__main__":
    print(json.dumps(manifest(), indent=2))

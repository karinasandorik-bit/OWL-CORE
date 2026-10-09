"""OWL Creative Engine v1: deterministic character DNA validator and compatibility gate.

Pure stdlib; this is a specification gate, NOT a 3D mesh or animation renderer.
"""
from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass
from typing import Any

SPEC = {
    "schema_version": "owl.character.v1",
    "id": "OWL-CHARACTER-003",
    "species": "owl",
    "visual_direction": ["high-fashion-tech", "cute", "editorial", "future-luxury"],
    "silhouette": {"ear_tuft_height_ratio": 0.19, "head_body_ratio": 0.72, "bilateral_symmetry": True},
    "eyewear": {"type": "technical-wraparound", "temple_route": "behind-ear-tuft-base", "bridge_anchor": "beak-above", "clearance_mm": 6},
    "rig": {"bones": ["root", "head", "beak", "lid_L", "lid_R", "wing_L", "wing_R", "tail", "ear_L", "ear_R"],
            "required_actions": ["blink", "gaze", "head_tilt", "wing_fold", "flight_idle"]},
    "materials": {"feathers": "anisotropic-soft", "glasses": "titanium-ceramic", "lens": "smoke-translucent"},
    "targets": ["GLB", "VRM", "iPhone-Safari-WebGL"],
}

class SpecError(ValueError):
    pass

def validate(spec: dict[str, Any]) -> None:
    if spec.get("schema_version") != "owl.character.v1":
        raise SpecError("Unsupported schema")
    if spec.get("species") != "owl":
        raise SpecError("OWL requires owl morphology")
    s = spec.get("silhouette", {})
    for field in ("ear_tuft_height_ratio", "head_body_ratio"):
        value = s.get(field)
        if type(value) not in (float, int) or not 0.05 <= value <= 1.0:
            raise SpecError("Invalid silhouette ratio: " + field)
    e = spec.get("eyewear", {})
    if e.get("temple_route") != "behind-ear-tuft-base" or e.get("bridge_anchor") != "beak-above":
        raise SpecError("Eyewear must be anatomically anchored")
    clearance = e.get("clearance_mm")
    if type(clearance) not in (float, int) or clearance < 3:
        raise SpecError("Insufficient eyewear clearance")
    rig = spec.get("rig", {})
    bones = rig.get("bones", [])
    actions = rig.get("required_actions", [])
    if not isinstance(bones, list) or not isinstance(actions, list):
        raise SpecError("Invalid rig")
    for pair in (("wing_L", "wing_R"), ("lid_L", "lid_R"), ("ear_L", "ear_R")):
        if any(x not in bones for x in pair):
            raise SpecError("Missing paired rig bones: " + str(pair))
    if not {"blink", "gaze", "head_tilt", "wing_fold", "flight_idle"} <= set(actions):
        raise SpecError("Missing required animation")
    if not {"GLB", "iPhone-Safari-WebGL"} <= set(spec.get("targets", [])):
        raise SpecError("Missing deployable target")

def fingerprint(spec: dict[str, Any]) -> str:
    validate(spec)
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def assessment(candidate: dict[str, Any]) -> dict[str, Any]:
    try:
        sha = fingerprint(candidate)
        return {"accepted": True, "sha256": sha, "stage": "SPEC_VALIDATED", "geometry_verified": False,
                "mesh_rendered": False, "device_tested": False}
    except (SpecError, TypeError, ValueError) as exc:
        return {"accepted": False, "reason": str(exc), "stage": "REJECTED"}

if __name__ == "__main__":
    print(json.dumps(assessment(SPEC), indent=2))

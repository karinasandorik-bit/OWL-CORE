# OWL Academy — Design Experiment 002

Date: 2026-10-10
Repository baseline: OWL-CORE/main README, unchanged. Prior experimental gate: owl-lab-training-001 (only numeric contrast and editable flag; no rendered UI).

## Artifact
Signal Bloom interactive HTML/CSS/JS prototype, delivered as the conversation attachment OWL_DESIGN_002.zip with screenshots, baseline.html, index.html, test_design.py, results.json. Source code is editable and has no external dependency.

## Predefined baseline
Minimal static HTML page with title, paragraph and non-operational Explore button. Compared on the same browser checks as candidate.

## Browser evaluation (executed)
Chromium via Playwright page.set_content: file:// and localhost browsing were blocked by environment administrator; in-memory DOM browser rendering worked.

Viewport widths: 390px and 1440px.
Tests (11): no horizontal overflow x2, no JS errors x2, functional navigation, theme toggle, JSON export, live status semantics, semantic nav, focus-visible styles, reduced-motion query.
Baseline: 4/11. Candidate: 11/11.
Browser-generated screenshots in downloadable artifact archive.

## Epistemic limits
- Author wrote candidate and evaluation: NOT independent, NOT blind, no externally authored holdout.
- No human taste rating, cross-browser test, robust accessibility audit, or original-art benchmark.
- Style checks for focus and reduced-motion are source-presence checks, not accessibility compliance.
- Candidate's JSON export records concept metadata, not full project state.
- No live deployment or recorded user acceptance.
- Outcome status: LOCALLY_VERIFIED_FUNCTIONAL_ONLY; EXTERNAL_VERIFICATION_PENDING.

## Next
Freeze candidate and invite evaluator to create unknown acceptance cases without access to baseline/candidate identity, run axe accessibility testing, real font/foreground color contrast, mobile/touch QA, and user preference study against credible designer-generated alternatives. Only promote a validated design capability if it survives those tests.

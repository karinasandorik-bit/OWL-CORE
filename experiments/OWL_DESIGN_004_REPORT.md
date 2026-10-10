# OWL Design 004 — Equal-Feature Visual Comparison

Date: 2026-10-10. Status: LOCALLY_VERIFIED_FUNCTIONAL; AESTHETIC_SUPERIORITY_UNPROVEN.

## Experimental design
Three existing task domains: editorial, fashion, research terminal. Two variants for each, at 390px and 1440px viewports. Variant A was the previously created OWL visual direction. Variant B is a neutral, coherent, accessible-looking alternative authored in the same session. Both use IDENTICAL semantic HTML content and JavaScript event handlers, with only CSS differences.

Chromium/Playwright direct content rendering executed. Tests assessed filter and bookmark actions, JS errors, horizontal overflow, clipped headings, and visual hierarchy sizes.

## Executed findings
- 6/6 viewports without horizontal overflow for A and B.
- 6/6 viewports with no JS runtime errors for both.
- Filter and bookmark functions passed on all six source variants.
- 6/6 viewports had no detected clipped card headings for both.
- Desktop heading/body ratio: A 9.00, B 4.13 (measure, not quality verdict).
- Mobile heading/body ratio: A 3.41, B 2.38.
- Zero external juror ratings; no aesthetic or originality superiority confirmed.

## Artifacts
Conversation artifact OWL_DESIGN_004.zip contains 6 runnable HTML versions, twelve screenshots, machine-readable metrics, source + evaluation script, an offline blind jury form, and blind order key.
SHA256 ZIP: b6f3ade698c98083a118900a308ac4dcda9b1a9a6067bcb6f39841a1f80ed80a

## Key limits
This is NOT independent comparison: same author created both visual systems; the second is not a professional competitor. These three domains are reused from an earlier task set, not independently authored holdouts. Script success cannot establish composition, originality, comprehension, or artistic power. Unscored blind review form is *prepared*, not completed. No claim of learned weights or sustained generalization.

## Promotion gate
Recruit ≥5 external blinded evaluators; assign randomized order, freeze sources, independently obtain 5+ unseen briefs, include strong professional reference designs under matched content and feature constraints; report pairwise preference with confidence intervals and disagreement. Assess user comprehension via timed tasks, comprehension quiz, and WCAG contrast/axe checks. Only promote artistic superiority if robust against these comparators and held-out tasks.

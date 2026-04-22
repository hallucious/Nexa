# Nexa Contract Review Product Specification

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: Product use-case specification
Authority scope: First killer use case, output shape, source referencing, and product meaning
Recommended path: `docs/specs/saas/contract_review_product_spec.md`

## 1. Purpose

This document defines the first real product use case of the Nexa SaaS: contract review for freelancers and sole proprietors.

Its purpose is to make the initial product promise explicit, so that:
- the SaaS is not just “an engine with a UI,”
- the first user outcome is concrete,
- and future implementation does not drift away from the intended value proposition.

## 2. User segment

The first intended user segment is:
- freelancers,
- sole proprietors,
- and similar independent workers reviewing contracts before signing.

The user is assumed to be:
- smart,
- non-specialist,
- and value-sensitive.

The product is not initially written for legal departments or enterprise contract operations teams.

## 3. Product promise

The initial promise is:

A user can upload a contract and receive:
1. extracted clauses worth attention,
2. plain-language explanations of why they matter,
3. and a practical list of pre-signature questions.

This is not a full legal opinion.
It is practical pre-signature decision support.

## 4. Use-case boundaries

The contract review use case does not promise:
- formal legal advice,
- enforceability guarantees,
- local-law completeness,
- or professional counsel replacement.

It promises:
- structured identification,
- understandable explanation,
- and actionable questions.

## 5. Canonical workflow

A conforming product flow is:

1. user selects contract review,
2. user uploads a contract file,
3. file becomes safe and usable,
4. a run is submitted,
5. the system processes the contract,
6. the user receives clause explanations and questions,
7. and the result preserves traceability back to source regions.

## 6. Functional decomposition

The baseline contract review pipeline has four conceptual stages:

1. document parsing,
2. clause extraction,
3. plain-language explanation,
4. question generation.

The product may implement these as nodes or equivalent execution stages, but the output meaning must remain the same.

## 7. Output requirements

The final result must include:

- a document reference,
- a clause list,
- plain-language explanation for each clause,
- and a list of pre-signature questions.

### 7.1 Clause object minimums

Each clause should preserve:
- clause id,
- relevant source text or source reference,
- severity/risk level,
- category,
- plain-language explanation,
- and why-it-matters framing.

### 7.2 Question object minimums

Each generated question should preserve:
- question text,
- related clause ids,
- and a priority marker.

## 8. Source-reference rule

The product must preserve meaningful source linkage from the final user-visible output back to the original uploaded document representation.

This rule matters because:
- explanations without traceability are harder to trust,
- and UI review becomes much weaker if results cannot be linked back to source regions.

The baseline source-linkage form is character-offset-based.
The exact rendering later may vary, but the linkage must survive.

## 9. Determinism rule for identifiers

The contract review output should generate stable clause identifiers from deterministic inputs.
The user should not see arbitrary clause IDs changing between equivalent reruns without cause.

## 10. Plain-language requirement

The explanation layer must optimize for:
- clarity,
- low jargon,
- practical relevance,
- and user comprehension.

The intended reading level is not specialist legal prose.

## 11. Priority and risk communication

The product must distinguish higher-risk issues from lower-risk ones in a structured way.

Risk signaling is not optional because the user needs triage, not just bulk extraction.

## 12. Product quality boundaries

A conforming output must not:
- fabricate authority,
- imply guaranteed legal correctness,
- or remove the distinction between assistance and legal counsel.

The product may be helpful without pretending to be a lawyer.

## 13. Template identity

The contract review flow should remain a recognized product template or starter experience, not a hidden internal configuration only.

This matters because the user-facing product needs a discoverable entry point for the first killer use case.

## 14. UX implications

The web layer should support:
- clause list rendering,
- question list rendering,
- source-region linking,
- and clear completion status.

The product should feel like a guided review tool, not a generic JSON viewer.

## 15. Non-goals

This specification does not require:
- redline generation,
- automated negotiation drafting,
- multi-party comparison,
- team approval workflow,
- or formal legal workflow integration.

Those may come later, but they are not baseline.

## 16. Acceptance criteria

This specification is satisfied only if all of the following are true:

1. a freelancer can upload a contract and complete the flow,
2. the output contains clause explanations and pre-signature questions,
3. source references are preserved,
4. risk or priority is visible,
5. explanations are understandable to a non-lawyer,
6. the product does not overclaim legal authority,
7. and the result is clearly recognizable as a contract-review product experience.

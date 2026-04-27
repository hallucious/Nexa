# Nexa Working Rules v2.0

Recommended save path: `docs/process/Nexa_Working_Rules_v2_0.md`

## 1. Core Objective

- Nexa’s top-level objective is commercial success through a trustworthy, extensible AI workflow/circuit engine.
- Balance engine quality, commercialization viability, efficiency, product clarity, and practical market fit.
- Avoid overbuilding before validating narrow high-value use cases, but do not ignore structural work that prevents rework or product risk.
- Nexa’s long-term product target is SaaS plus mobile app, not desktop-first packaging.

## 2. Architecture Principles

- Nexa follows the Architecture Constitution: Circuit → Node → Runtime → Prompt/Provider/Plugin → Artifact → Trace.
- Node is the sole execution unit.
- Execution must be dependency-driven, not simple pipeline fallback.
- Artifacts are append-only.
- Execution should be deterministic where applicable.
- Plugin namespace write restrictions and contract-driven architecture are core invariants.
- Keep the pure engine core small and stable. Optional, tierable, removable, experimental, or auxiliary features must be modular and attach/detach cleanly at dependency/interface boundaries.
- Maintain alignment between program function, code structure, file structure, contracts, and user-facing behavior.
- Prioritize extensibility, efficiency, commercialization viability, and legal/API-policy compliance.

## 3. Session Start Protocol

- At the start of Nexa coding/design/debug sessions, identify: MODE, Gate/Step/Phase or current project position, latest/base commit if inferable, and single session objective.
- Modes are DISCUSSION, DESIGN, IMPLEMENT, and DEBUG.
- Do not switch modes without the user’s explicit approval unless the user clearly requested the new mode.
- Before implementation, review the relevant source, latest handoff/plan/docs if available, and prerequisite files needed for the task.
- Do not ask the user for information already inferable from the uploaded Zip filename, immediately preceding commit note, conversation context, or available project files.

## 4. Zip / Source / Commit Note Handling

- When the user uploads a Zip after a commit-note workflow, infer the base commit hash from the Zip filename if present.
- Use the immediately preceding commit note written in the conversation as the source for the changed-file list; do not look for the commit note inside the Zip unless the user explicitly says it is there.
- First inspect only the files listed in the immediately preceding commit note.
- Expand only to directly related dependency, contract, or test files when needed.
- Do not perform a full Zip/repo scan by default.
- Ask the user for the commit note, changed-file list, or base hash only if the conversation context is unavailable/truncated, the filename lacks a usable hash, or the note/filename/files conflict.
- If files were changed outside my access or latest file state is uncertain, ask for the latest relevant files before editing.

## 5. Coding Rules

- The user is not a programmer; explain coding actions in non-developer-friendly steps.
- Do not guess when code/file state is unclear. State uncertainty and request the needed file/context.
- For code changes, modify the actual files and provide complete modified files via downloadable artifacts, not only snippets.
- When providing code in chat is necessary, provide a full copy-paste-ready single block.
- Do not provide temporary, cosmetic, or “looks working” fixes without root-cause reasoning.
- Consider future file interconnections and extensibility before changing code.
- If a task is impossible or a better standard implementation exists, say so clearly.
- For Nexa, the assistant should directly perform coding work when feasible rather than delegating coding to Claude. Claude prompts are only for explicit prompt-preparation tasks or when strategically appropriate and requested.

## 6. Debugging Rules

- DEBUG mode sequence is fixed: reproduce conditions → top 3 likely causes → verify the most likely cause first → fix → derive recurrence-prevention rule.
- For unstable/recurrent bugs, propose a reproducible debug package or targeted regression test.
- Do not patch blindly.

## 7. Testing & Verification Rules

- Before delivering modified code files, run only the tests directly related to the changed files or affected area by default.
- Do not run full pytest by default before file delivery.
- Run broader/full regression only when structural/contract/runtime/import changes justify it, when the user provides full-test results, or before major backup/release decisions if necessary.
- Do not create tests for example/demo circuits unless explicitly requested.
- If tests fail, do not deliver files as passed. Report the failure and fix or explain.
- When the user provides test results, respond with Git backup commands immediately when appropriate.

## 8. Documentation & Spec Rules

- New features or technologies that require specification must be documented before implementation.
- Documentation sync should be batched after every 5 implemented features or when a logical sector completes, unless code-contract-doc inconsistency blocks implementation.
- Documentation must accumulate valid content and remove only truly obsolete content.
- Documents should be detailed, English spec style, unambiguous for future AI/human readers, and use numbering starting from 1.
- Always provide recommended save paths for new or updated documents.
- For documents, provide both copy-paste-ready single blocks and downloadable files when delivering artifacts.
- Preserve the current document governance: BLUEPRINT as upper index, specs/ as SemVer independent specs, STRATEGY where relevant, and current planning baseline no longer assumed to be TRACKER if it has been deleted or deprecated by the user.

## 9. Artifact Delivery Rules

- Before providing download links, verify files actually exist.
- Provide sandbox links.
- For modified coding files, provide individual download links and also a Zip archive.
- Zip archives should preserve recommended repository save paths and include only files actually modified in the task, unless the user explicitly asks otherwise.
- Do not include unnecessary full-repo packages.
- Test result reports do not need to be generated as separate files unless requested.
- Always state the base commit hash used for the work when providing result files, if inferable.

## 10. Git Backup & Obsidian Rules

- Use GitHub main branch only for backups.
- Prefer `git add .` for commit preparation.
- Do not include `git switch main` or `git rev-parse --short HEAD` in backup command instructions.
- After work completion, GitHub main backup and Obsidian 1:1 note belong together.
- Every commit should have a corresponding Obsidian note.
- Git note title format: `YYYY-MM-DD__[]_<short-description>`; no `#` symbols in titles. Title and Body must be separate blocks.
- Obsidian note body should be English spec style and include summary, background, decisions, implementation, verification, artifacts/results, risks, and next work.

## 11. Scope / Refactoring / Seam Rules

- Work should maximize overall project progress and bottleneck removal, not local polishing.
- Polishing is not automatically forbidden; do it when it materially reduces structural risk, prevents rework, improves real usability, or unlocks the next phase.
- For connected structural debt, batch related work efficiently instead of handling it one tiny step at a time.
- For seam tasks, first survey all remaining seams, plan the batch, then implement related seams together.
- Within a sector, prefer order: implementation → seam work → other necessary cleanup, except critical seams that block implementation.
- If old/contradictory project source content is found, notify the user and recommend deletion or correction.
- During refactors, delete files that have no remaining structural value once non-use or duplication is confirmed; do not keep legacy/quarantine files unnecessarily.

## 12. Commercial / Legal / Cost Rules

- Avoid legal/IP/API-policy risks and reject unsafe or policy-violating implementation requests rather than attempting workarounds.
- Nexa should avoid external-source obligations that create fees to outside organizations for commercial operation.
- Software development/operation costs for Nexa itself should be avoided where possible.
- Cost responsibility model: the operation AI used to run Nexa is paid by the user; Designer AI and Provider AI inside user-created circuits are paid by the end user.
- Use OpenAI/Anthropic/Google API policy compliance as a design constraint.

## 13. Communication Rules

- Be direct if the user is wrong; do not falsely agree.
- Present user-facing next action as one step when asking the user to act, but internally batch connected work efficiently.
- Avoid repeating already explained content unless needed.
- Proactively warn about structural risks, better standard approaches, low-value work, rework risk, or commercialization problems.
- Explain status as current situation → cause → action → state, especially for coding tasks.

## 14. External AI / Claude Rules

- For Nexa, default is direct implementation by the assistant unless the user explicitly asks for Claude prompt preparation.
- If preparing Claude prompts, include model recommendation and whether extended thinking should be used.
- Use Claude Sonnet for complex architecture/runtime/contract/debugging/refactor tasks; use cheaper/faster models only for small isolated edits/tests when appropriate.
- When asking Claude to code, provide the codebase or minimal diff context plus task prompt, architecture constraints, safety scanner/checklist, output contract, and list of files to provide.
- Diff-based compressed prompts are preferred when applicable.

## 15. Deprecated / Superseded Guidance

- “Always full pytest before file delivery” is superseded by “run related tests by default; full pytest only when justified.”
- “Always ask for commit hash / commit note / changed-file list” is superseded by “infer from Zip filename and immediately preceding commit note when possible.”
- “Always update docs after every code change” is superseded by batched documentation sync unless docs/specs are prerequisite or inconsistency blocks work.
- “Never provide zip” is superseded by “provide individual links plus path-preserving zip containing modified files only.”
- “Do one step only” applies to user-facing requested next actions, not internal execution; internally batch rationally and efficiently.

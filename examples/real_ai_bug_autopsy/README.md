# Real AI Bug Autopsy Demo

This demo uses a real AI provider through `provider_ref: ai`.

## Required

Set one real provider API key in your environment or `.env`:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `PPLX_API_KEY`

## Run

```bash
nexa run examples/real_ai_bug_autopsy/run_a.nex --state examples/real_ai_bug_autopsy/state.json --out run_a.json
nexa run examples/real_ai_bug_autopsy/run_b.nex --state examples/real_ai_bug_autopsy/state.json --out run_b.json
nexa diff run_a.json run_b.json
nexa export run_a.json --out run_a_audit.zip
nexa replay run_a_audit.zip --strict
```

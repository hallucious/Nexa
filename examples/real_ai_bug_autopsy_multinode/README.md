# Real AI Bug Autopsy (Multinode Demo)

This demo shows how a small difference in the first node input propagates through a multi-node AI workflow.

## Run

```bash
nexa run examples/real_ai_bug_autopsy_multinode/run_a.nex --state examples/real_ai_bug_autopsy_multinode/state.json --out run_a.json
nexa run examples/real_ai_bug_autopsy_multinode/run_b.nex --state examples/real_ai_bug_autopsy_multinode/state.json --out run_b.json
```

## Compare

```bash
nexa diff run_a.json run_b.json
```

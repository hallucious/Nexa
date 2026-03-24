# Real AI Divergence Demo (Investment Decision)

## 🔥 What This Demo Shows

This demo proves a simple but critical fact:

> **A single word change in AI interpretation can flip a real decision.**

---

## ⚡ Key Idea

* Same input data
* Only ONE word changed in the AI lens
* Completely different outcome

---

## 🧪 Experiment Setup

### Input (identical)

A company description with:

* revenue growth
* SaaS recurring model
* low churn
* stable management
* some customer concentration risk

---

### A vs B Difference

| Run | AI Lens    |
| --- | ---------- |
| A   | continuity |
| B   | fragility  |

That is the **only intentional difference**.

---

## ▶️ How to Run

```bash
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_A.nex --out run_a.json
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_B.nex --out run_b.json
nexa diff examples/real_ai_bug_autopsy_multinode/runs/run_a.json examples/real_ai_bug_autopsy_multinode/runs/run_b.json
```

> When `--out` is given as a bare filename, Nexa writes the snapshot into the demo's `runs/` directory.

---

## 📊 Expected Result

### Run A (continuity)

* score: low (for example, around 20)
* decision: **INVEST**

---

### Run B (fragility)

* score: high (for example, around 70)
* decision: **DO_NOT_INVEST**

---

## 🔍 What You’ll See in the Diff

```text
Node2 → AI interpretation changed
Node3 → score changed
Node4 → decision flipped
```

---

## 🧠 Why This Matters

Typical AI usage often looks like this:

* same input → different output
* no precise explanation of where the change began
* no reliable run-to-run comparison path
* no clean debugging surface

---

## 🧩 What Nexa Does

Nexa turns AI workflows into:

* traceable execution
* deterministic downstream logic where possible
* diffable run outputs
* reproducible investigation artifacts

---

## 🏗️ Execution Structure

```text
Node1: Normalize input (deterministic)
Node2: AI interpretation (provider-backed)
Node3: Score from interpreted signal (deterministic)
Node4: Final decision from score (deterministic)
```

Nexa does not force this demo through a global fixed pipeline.
Each node executes according to dependency satisfaction, and the diff compares the resulting run artifacts.

---

## ⚠️ Environment Note

If the demo behaves unexpectedly on Windows or PowerShell, check whether an old shell-level `OPENAI_API_KEY` is already set.
A shell environment variable can take precedence over values loaded from `.env`, which may cause the run to use a different key than expected.

---

## 🎯 Core Insight

> AI is not deterministic — but your system can still be inspectable.

Nexa isolates where model variability happens and makes downstream reasoning easier to trace, compare, and debug.

---

## 🧪 Why This Demo Is Important

This is not a toy example.

It demonstrates:

* AI reasoning variability
* controlled propagation into decisions
* full traceability from upstream interpretation change to downstream decision flip

---

## 🚀 Next Steps

Try modifying:

* the lens word
* the scoring logic
* the decision threshold

Then compare the new run output against the baseline snapshots.

---

## 🏁 Conclusion

Nexa does not try to make AI deterministic.

It makes AI **understandable, comparable, and debuggable**.

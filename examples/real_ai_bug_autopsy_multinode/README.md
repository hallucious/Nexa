# Real AI Divergence Demo (Investment Decision)

## 🔥 What This Demo Shows

This demo proves a simple but critical fact:

> **A single word change in AI interpretation can flip a real decision.**

---

## ⚡ Key Idea

* Same input data
* Only ONE word changed in AI prompt
* Completely different outcome

---

## 🧪 Experiment Setup

### Input (identical)

A company description:

* Revenue growth
* SaaS recurring model
* Low churn
* Stable management
* Some customer concentration risk

---

### A vs B Difference

| Run | AI Lens    |
| --- | ---------- |
| A   | continuity |
| B   | fragility  |

That’s the **only difference**.

---

## ▶️ How to Run

```bash
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_A.nex --out run_a.json
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_B.nex --out run_b.json
nexa diff run_a.json run_b.json
```

---

## 📊 Expected Result

### Run A (continuity)

* score: low (e.g., ~20)
* decision: **INVEST**

---

### Run B (fragility)

* score: high (e.g., ~70)
* decision: **DO_NOT_INVEST**

---

## 🔍 What You’ll See in Diff

```text
Node2 → AI interpretation changed
Node3 → score changed
Node4 → decision flipped
```

---

## 🧠 Why This Matters

Typical AI systems:

* Same input → different output
* ❌ No explanation
* ❌ No reproducibility
* ❌ No debugging

---

## 🧩 What Nexa Does

Nexa turns AI workflows into:

* ✔️ Traceable execution
* ✔️ Deterministic downstream logic
* ✔️ Diffable outputs

---

## 🏗️ Pipeline Structure

```text
Node1: Normalize input (deterministic)
Node2: AI interpretation (non-deterministic)
Node3: Score (deterministic)
Node4: Decision (deterministic)
```

---

## 🎯 Core Insight

> AI is not deterministic — but your system can be.

Nexa isolates where randomness happens
and makes everything else predictable and debuggable.

---

## 🧪 Why This Demo Is Important

This is not a toy example.

It demonstrates:

* AI reasoning variability
* Controlled propagation into decisions
* Full traceability of cause → effect

---

## 🚀 Next Steps

Try modifying:

* the lens word
* the scoring logic
* the decision threshold

and observe how the system behaves.

---

## 🏁 Conclusion

Nexa doesn't try to make AI deterministic.

It makes AI **understandable**.

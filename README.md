# Nexa — Make AI Execution Deterministic, Traceable, and Debuggable

## 🔥 What This Demo Shows

Same input.
One word changed.
Completely different decision.

```bash
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_A.nex --out run_a.json
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_B.nex --out run_b.json
nexa diff run_a.json run_b.json
```

## 💥 Result

* A (lens: continuity) → INVEST
* B (lens: fragility) → DO_NOT_INVEST

**Only one word changed.**

---

## 🧠 Why This Matters

AI systems are **not deterministic**.

Same input → different output
But:

* You don’t know why
* You can’t reproduce it
* You can’t debug it

---

## 🧩 Nexa Fixes This

Nexa turns AI execution into:

* **Deterministic pipeline**
* **Traceable reasoning flow**
* **Diffable outputs**

---

## 🔍 What Actually Happened

```text
Node2 (AI interpretation changed)
→ Node3 (score changed)
→ Node4 (decision flipped)
```

You can see exactly:

* where it changed
* how much it changed
* why the final result changed

---

## ⚙️ How It Works

Each AI workflow is a **circuit**:

* Node1: deterministic normalization
* Node2: AI interpretation
* Node3: deterministic scoring
* Node4: deterministic decision

---

## 📊 Example Diff (Real Output)

```text
Node2: interpretation changed
Node3: score 20 → 75
Node4: INVEST → DO_NOT_INVEST
```

---

## 🚀 Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Set API Key

```bash
export OPENAI_API_KEY="your_api_key"
```

### 3. Run Demo

```bash
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_A.nex --out run_a.json
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_B.nex --out run_b.json
nexa diff run_a.json run_b.json
```

---

## 🧪 What Makes Nexa Different

| Problem         | Traditional AI | Nexa |
| --------------- | -------------- | ---- |
| Reproducibility | ❌              | ✔️   |
| Debugging       | ❌              | ✔️   |
| Causal tracing  | ❌              | ✔️   |
| Output diff     | ❌              | ✔️   |

---

## 🎯 Core Idea

> AI should not be a black box.
> It should be a **traceable system.**

---

## 📌 Status

* ✅ Real AI divergence demo complete
* ✅ Deterministic execution engine
* ✅ Trace + diff system working

---

## 🧠 Future

* Multi-agent circuits
* Debate / consensus workflows
* Self-debugging AI pipelines

---

## 🏁 Conclusion

Nexa doesn’t make AI smarter.

It makes AI **understandable**.

# Plugin System

Plugins extend nodes with non-AI computation capabilities.

See contract: `docs/specs/contracts/plugin_contract.md`

---

# Plugin Responsibilities

* data transformation
* ranking outputs
* formatting results
* validation and evaluation
* filtering

---

# When Plugins Execute

Plugins execute within node phases:

* **pre**: data preparation before the AI call
* **core**: tool calls alongside the AI call
* **post**: output processing after the AI call

The order in which a plugin runs depends on the node's execution configuration, not a fixed system pipeline.

---

# Plugin Write Restrictions (Strict)

```
plugin.<plugin_id>.*    ← allowed

prompt.*                ← forbidden
provider.*              ← forbidden
output.*                ← forbidden
artifact.*              ← forbidden
input.*                 ← forbidden
```

---

# Plugin Result Contract

```python
PluginResult:
    success: bool
    output: dict | None
    error: str | None
    latency_ms: int
    reason_code: str | None
    stage: str | None  # PRE | CORE | POST
```

---

# Plugin Safety Model

Plugins must:
* avoid modifying core runtime structures
* avoid side effects outside allowed namespace
* produce deterministic results given the same inputs

---

# Plugin Registry

Managed by `src/platform/plugin_registry.py`.

See contract: `docs/specs/contracts/plugin_registry_contract.md`

---

End of Plugin System Document

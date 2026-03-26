from typing import Dict

PROMPT_REGISTRY: Dict[str, Dict[str, object]] = {
    "g1_design@v1": {
        "file": "g1_design.v1.prompt.txt",
        "required": ["request_text"],
    },
    "g2_continuity@v1": {
        "file": "g2_continuity.v1.prompt.txt",
        "required": ["pic_text", "current_text"],
    },
    "g4_self_check@v1": {
        "file": "g4_self_check.v1.prompt.txt",
        "required": [],
    },
    "g6_counterfactual@v1": {
        "file": "g6_counterfactual.v1.prompt.txt",
        "required": ["g1_output_json"],
    },
    "g7_final_review@v1": {
        "file": "g7_final_review.v1.prompt.txt",
        "required": ["decision", "baseline_present"],
    },
}

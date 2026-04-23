from pathlib import Path
import json

from src.cli.nexa_cli import save_output
from src.contracts.provider_contract import ProviderError, ProviderResult


def test_save_output_serializes_provider_result(tmp_path: Path):
    payload = {
        "result": {
            "state": {
                "node1": {
                    "output": ProviderResult(
                        output="hello",
                        raw_text="hello",
                        structured=None,
                        artifacts=[],
                        trace={"provider": "fake"},
                        error=ProviderError(type="x", message="y", retryable=False),
                    )
                }
            }
        }
    }

    out = tmp_path / "out.json"
    save_output(payload, out)

    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["result"]["state"]["node1"]["output"]["output"] == "hello"
    assert loaded["result"]["state"]["node1"]["output"]["trace"]["provider"] == "fake"
    assert loaded["result"]["state"]["node1"]["output"]["error"]["type"] == "x"

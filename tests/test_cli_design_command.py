from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.cli.nexa_cli import build_parser, main
from src.contracts.savefile_factory import make_minimal_savefile
from src.contracts.savefile_serializer import save_savefile_file


@dataclass(frozen=True)
class _FakeBundle:
    request_text: str
    target_working_save_ref: str | None
    rendered_preview: str


class _FakeProposalFlow:
    def __init__(self, *, normalizer=None):
        self.normalizer = normalizer

    def propose(self, request_text: str, *, working_save_ref: str | None = None, session_state_card=None):
        storage_role = getattr(session_state_card, 'storage_role', 'none') if session_state_card is not None else 'none'
        preview = f"preview::{request_text}::{storage_role}"
        return _FakeBundle(
            request_text=request_text.strip(),
            target_working_save_ref=working_save_ref,
            rendered_preview=preview,
        )


class _FakeNormalizer:
    def __init__(self, **kwargs):
        self.kwargs = kwargs



def _write_valid_savefile(path: Path) -> None:
    savefile = make_minimal_savefile(
        name="designer_context",
        version="1.0.0",
        description="Designer context artifact",
        entry="node1",
        node_type="plugin",
        resource_ref={"plugin": "plugin.main"},
        plugins={"plugin.main": {"entry": "plugins.example.run"}},
        ui_metadata={"created_by": "test"},
    )
    save_savefile_file(savefile, str(path))



def test_cli_parser_accepts_design_command_options() -> None:
    parser = build_parser()

    args = parser.parse_args([
        "design",
        "reviewer에 Claude 붙여줘",
        "--save",
        "ws-001",
        "--artifact",
        "demo.nex",
        "--backend",
        "claude",
        "--json",
        "--out",
        "proposal.json",
    ])

    assert args.command == "design"
    assert args.request_text == "reviewer에 Claude 붙여줘"
    assert args.working_save_ref == "ws-001"
    assert args.artifact == "demo.nex"
    assert args.backend == "claude"
    assert args.output_json is True
    assert args.out == "proposal.json"



def test_design_command_prints_rendered_preview_by_default(monkeypatch, capsys) -> None:
    monkeypatch.setattr("src.designer.proposal_flow.DesignerProposalFlow", _FakeProposalFlow)
    monkeypatch.setattr("src.cli.nexa_cli.DesignerRequestNormalizer", _FakeNormalizer, raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "design", "Add a review node before final output", "--save", "ws-001"],
    )

    exit_code = main()

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "preview::Add a review node before final output::none" in out



def test_design_command_emits_json_and_writes_output_file(monkeypatch, tmp_path, capsys) -> None:
    out_path = tmp_path / "proposal.json"
    monkeypatch.setattr("src.designer.proposal_flow.DesignerProposalFlow", _FakeProposalFlow)
    monkeypatch.setattr("src.cli.nexa_cli.DesignerRequestNormalizer", _FakeNormalizer, raising=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "design",
            "Change the reviewer provider to Claude.",
            "--save",
            "ws-002",
            "--json",
            "--out",
            str(out_path),
        ],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["command"] == "design"
    assert payload["target_working_save_ref"] == "ws-002"
    assert out_path.exists()
    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved["command"] == "design"
    assert saved["request_text"] == "Change the reviewer provider to Claude."



def test_design_command_loads_artifact_context_for_existing_circuit(monkeypatch, tmp_path, capsys) -> None:
    artifact_path = tmp_path / "designer_context.nex"
    _write_valid_savefile(artifact_path)
    monkeypatch.setattr("src.designer.proposal_flow.DesignerProposalFlow", _FakeProposalFlow)
    monkeypatch.setattr("src.cli.nexa_cli.DesignerRequestNormalizer", _FakeNormalizer, raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "design", "Explain this circuit", "--artifact", str(artifact_path)],
    )

    exit_code = main()

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "preview::Explain this circuit::working_save" in out



def test_design_command_reports_error_for_unloadable_artifact(monkeypatch, tmp_path, capsys) -> None:
    artifact_path = tmp_path / "broken.nex"
    artifact_path.write_text('{"meta": {}}', encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["nexa", "design", "Explain this circuit", "--artifact", str(artifact_path)])

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["command"] == "design"
    assert "Unable to load Designer artifact context" in payload["message"]

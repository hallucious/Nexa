from __future__ import annotations

from types import SimpleNamespace

from src.pipeline.cli import _exit_code_after_drift


def test_fail_on_hard_drift_enabled_hard_drift_returns_2() -> None:
    report = SimpleNamespace(hard_drift=[1], soft_drift=[])
    assert _exit_code_after_drift(report=report, fail_on_hard_drift=True) == 2


def test_fail_on_hard_drift_enabled_no_hard_drift_returns_0() -> None:
    report = SimpleNamespace(hard_drift=[], soft_drift=[1])
    assert _exit_code_after_drift(report=report, fail_on_hard_drift=True) == 0


def test_fail_on_hard_drift_disabled_returns_0_even_if_hard_drift() -> None:
    report = SimpleNamespace(hard_drift=[1], soft_drift=[])
    assert _exit_code_after_drift(report=report, fail_on_hard_drift=False) == 0


def test_fail_on_hard_drift_none_report_returns_0() -> None:
    assert _exit_code_after_drift(report=None, fail_on_hard_drift=True) == 0

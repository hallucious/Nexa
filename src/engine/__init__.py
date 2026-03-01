"""Hyper-AI Engine (v1 skeleton).

This package is the canonical home for Engine/Node/Revision primitives.
Contract source of truth: docs/specs/* (Engine v1.0.0 set).
"""
from .engine import Engine
from .node import Node, NodeResult, StageResult, StageStatus, NodeStatus
from .revision import Revision
from .fingerprint import StructuralFingerprint

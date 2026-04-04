from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from src.designer.models.circuit_patch_plan import CircuitPatchPlan, PatchOperation
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_commit_candidate import DesignerCommitCandidateState
from src.designer.proposal_flow import DesignerProposalBundle
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import (
    DesignerDraftModel,
    RuntimeModel,
    UIModel,
    WorkingSaveMeta,
    WorkingSaveModel,
)


@dataclass(frozen=True)
class DesignerPatchApplicationResult:
    candidate_working_save: WorkingSaveModel
    patch_ref: str
    applied_operation_ids: tuple[str, ...]
    created_node_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class DesignerPatchApplier:
    """Step 4 bridge: patch plan -> proposal-applied candidate Working Save.

    This class materializes a candidate Working Save from an existing Working
    Save plus an explicit CircuitPatchPlan. It does not cross the approval or
    commit boundary and it does not create Commit Snapshots by itself.
    """

    def apply_patch(
        self,
        base_working_save: WorkingSaveModel,
        patch: CircuitPatchPlan,
        *,
        intent_ref: str | None = None,
        precheck_ref: str | None = None,
        preview_ref: str | None = None,
    ) -> DesignerPatchApplicationResult:
        nodes = deepcopy(base_working_save.circuit.nodes)
        edges = deepcopy(base_working_save.circuit.edges)
        outputs = deepcopy(base_working_save.circuit.outputs)
        resources = ResourcesModel(
            prompts=deepcopy(base_working_save.resources.prompts),
            providers=deepcopy(base_working_save.resources.providers),
            plugins=deepcopy(base_working_save.resources.plugins),
        )
        state = StateModel(
            input=deepcopy(base_working_save.state.input),
            working=deepcopy(base_working_save.state.working),
            memory=deepcopy(base_working_save.state.memory),
        )
        runtime_errors = list(deepcopy(base_working_save.runtime.errors))
        warnings: list[str] = []
        created_node_ids: list[str] = []

        for operation in patch.operations:
            created = self._apply_operation(operation, nodes, edges, outputs, warnings)
            if created:
                created_node_ids.extend(created)

        designer_data = deepcopy(base_working_save.designer.data if base_working_save.designer else {})
        designer_data.update(
            {
                "candidate_origin": "designer_patch_application",
                "last_applied_patch_ref": patch.patch_id,
                "last_intent_ref": intent_ref,
                "last_precheck_ref": precheck_ref,
                "last_preview_ref": preview_ref,
                "applied_operation_ids": [operation.op_id for operation in patch.operations],
                "created_node_ids": created_node_ids,
                "application_warnings": warnings,
            }
        )

        runtime_validation_summary = deepcopy(base_working_save.runtime.validation_summary)
        runtime_validation_summary.update(
            {
                "designer_patch_ref": patch.patch_id,
                "applied_operation_count": len(patch.operations),
                "touch_mode": patch.change_scope.touch_mode,
                "requires_confirmation": patch.risk_report.requires_confirmation,
            }
        )

        candidate = WorkingSaveModel(
            meta=WorkingSaveMeta(
                format_version=base_working_save.meta.format_version,
                storage_role="working_save",
                name=base_working_save.meta.name,
                description=base_working_save.meta.description,
                created_at=base_working_save.meta.created_at,
                updated_at=base_working_save.meta.updated_at,
                working_save_id=base_working_save.meta.working_save_id,
            ),
            circuit=CircuitModel(
                nodes=nodes,
                edges=edges,
                entry=self._updated_entry(base_working_save.circuit.entry, patch.operations),
                outputs=outputs,
            ),
            resources=resources,
            state=state,
            runtime=RuntimeModel(
                status="ready_for_review",
                validation_summary=runtime_validation_summary,
                last_run=deepcopy(base_working_save.runtime.last_run),
                errors=runtime_errors,
            ),
            ui=UIModel(
                layout=deepcopy(base_working_save.ui.layout),
                metadata=deepcopy(base_working_save.ui.metadata),
            ),
            designer=DesignerDraftModel(data=designer_data),
        )
        return DesignerPatchApplicationResult(
            candidate_working_save=candidate,
            patch_ref=patch.patch_id,
            applied_operation_ids=tuple(operation.op_id for operation in patch.operations),
            created_node_ids=tuple(created_node_ids),
            warnings=tuple(warnings),
        )

    def apply_bundle(
        self,
        base_working_save: WorkingSaveModel,
        bundle: DesignerProposalBundle,
    ) -> DesignerPatchApplicationResult:
        return self.apply_patch(
            base_working_save,
            bundle.patch,
            intent_ref=bundle.intent.intent_id,
            precheck_ref=bundle.precheck.precheck_id,
            preview_ref=bundle.preview.preview_id,
        )

    def build_commit_candidate_state(
        self,
        application: DesignerPatchApplicationResult,
        approval_state: DesignerApprovalFlowState,
        *,
        source_working_save_ref: str | None = None,
    ) -> DesignerCommitCandidateState:
        designer_data = application.candidate_working_save.designer.data if application.candidate_working_save.designer is not None else {}
        candidate_ref = application.candidate_working_save.meta.working_save_id or application.candidate_working_save.meta.name
        return DesignerCommitCandidateState(
            approval_id=approval_state.approval_id,
            intent_ref=str(designer_data.get("last_intent_ref") or approval_state.intent_ref),
            patch_ref=application.patch_ref,
            precheck_ref=str(designer_data.get("last_precheck_ref") or approval_state.precheck_ref),
            preview_ref=str(designer_data.get("last_preview_ref") or approval_state.preview_ref),
            approval_stage=approval_state.current_stage,
            approval_outcome=approval_state.final_outcome,
            ready_for_commit=approval_state.commit_eligible,
            source_working_save_ref=source_working_save_ref,
            candidate_working_save_ref=candidate_ref,
            validated_scope_ref=approval_state.validated_scope_ref,
            approved_scope_ref=approval_state.approved_scope_ref,
            applied_operation_ids=application.applied_operation_ids,
            created_node_ids=application.created_node_ids,
            candidate_origin=str(designer_data.get("candidate_origin") or "designer_patch_application"),
        )

    def _apply_operation(
        self,
        operation: PatchOperation,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
        warnings: list[str],
    ) -> list[str]:
        handler_name = f"_handle_{operation.op_type}"
        handler = getattr(self, handler_name, None)
        if handler is None:
            warnings.append(f"Unsupported patch operation was skipped: {operation.op_type}")
            return []
        return handler(operation, nodes, edges, outputs, warnings)

    def _handle_create_node(
        self,
        operation: PatchOperation,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
        warnings: list[str],
    ) -> list[str]:
        payload = operation.payload
        requested_id = payload.get("node_id") or operation.target_ref or "node.created"
        node_id = self._resolve_created_node_id(nodes, requested_id, payload)
        node = {
            "id": node_id,
            "kind": payload.get("kind", "generic"),
            "metadata": {k: v for k, v in payload.items() if k not in {"node_id", "insert_after", "kind"}},
        }
        nodes.append(node)

        insert_after = payload.get("insert_after")
        if insert_after and self._try_resolve_node_id(nodes, insert_after):
            self._ensure_edge(edges, insert_after, node_id)

        if payload.get("kind") == "review_gate" and operation.target_ref:
            target_id = self._resolve_existing_node_id(nodes, operation.target_ref)
            self._ensure_edge(edges, target_id, node_id)
            self._reroute_outputs(outputs, target_id, node_id)

        return [node_id]

    def _handle_delete_node(
        self,
        operation: PatchOperation,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
        warnings: list[str],
    ) -> list[str]:
        node_id = self._resolve_existing_node_id(nodes, operation.target_ref)
        nodes[:] = [node for node in nodes if self._node_id(node) != node_id]
        edges[:] = [edge for edge in edges if self._edge_from(edge) != node_id and self._edge_to(edge) != node_id]
        return []

    def _handle_update_node_metadata(self, operation, nodes, edges, outputs, warnings):
        node = self._resolve_node(nodes, operation.target_ref)
        metadata = deepcopy(node.get("metadata", {}))
        metadata.update(operation.payload)
        node["metadata"] = metadata
        return []

    def _handle_set_node_provider(self, operation, nodes, edges, outputs, warnings):
        node = self._resolve_node(nodes, operation.target_ref)
        provider_id = operation.payload.get("provider_id")
        resource_ref = deepcopy(node.get("resource_ref", {}))
        resource_ref["provider"] = provider_id
        node["resource_ref"] = resource_ref
        execution = deepcopy(node.get("execution", {}))
        provider_block = deepcopy(execution.get("provider", {}))
        provider_block["provider_id"] = provider_id
        execution["provider"] = provider_block
        node["execution"] = execution
        return []

    def _handle_attach_node_plugin(self, operation, nodes, edges, outputs, warnings):
        node = self._resolve_node(nodes, operation.target_ref)
        plugin_id = operation.payload.get("plugin_id")
        plugin_refs = list(deepcopy(node.get("plugin_refs", [])))
        if plugin_id and plugin_id not in plugin_refs:
            plugin_refs.append(plugin_id)
        node["plugin_refs"] = plugin_refs
        return []

    def _handle_detach_node_plugin(self, operation, nodes, edges, outputs, warnings):
        node = self._resolve_node(nodes, operation.target_ref)
        plugin_id = operation.payload.get("plugin_id")
        plugin_refs = [value for value in deepcopy(node.get("plugin_refs", [])) if value != plugin_id]
        node["plugin_refs"] = plugin_refs
        return []

    def _handle_set_node_prompt(self, operation, nodes, edges, outputs, warnings):
        node = self._resolve_node(nodes, operation.target_ref)
        prompt_id = operation.payload.get("prompt_id") or operation.payload.get("prompt_ref")
        resource_ref = deepcopy(node.get("resource_ref", {}))
        resource_ref["prompt"] = prompt_id
        node["resource_ref"] = resource_ref
        execution = deepcopy(node.get("execution", {}))
        provider_block = deepcopy(execution.get("provider", {}))
        provider_block["prompt_ref"] = prompt_id
        execution["provider"] = provider_block
        node["execution"] = execution
        return []

    def _handle_set_parameter(self, operation, nodes, edges, outputs, warnings):
        node = self._resolve_node(nodes, operation.target_ref)
        parameters = deepcopy(node.get("parameters", {}))
        parameters.update(operation.payload)
        node["parameters"] = parameters
        return []

    def _handle_connect_nodes(self, operation, nodes, edges, outputs, warnings):
        source = operation.payload.get("from") or operation.payload.get("source") or operation.target_ref
        target = operation.payload.get("to") or operation.payload.get("target")
        if not source or not target:
            warnings.append(f"connect_nodes skipped because endpoints were incomplete for {operation.op_id}")
            return []
        source_id = self._resolve_existing_node_id(nodes, source)
        target_id = self._resolve_existing_node_id(nodes, target)
        self._ensure_edge(edges, source_id, target_id)
        return []

    def _handle_disconnect_nodes(self, operation, nodes, edges, outputs, warnings):
        source = operation.payload.get("from") or operation.payload.get("source") or operation.target_ref
        target = operation.payload.get("to") or operation.payload.get("target")
        if not source or not target:
            warnings.append(f"disconnect_nodes skipped because endpoints were incomplete for {operation.op_id}")
            return []
        source_id = self._resolve_existing_node_id(nodes, source)
        target_id = self._resolve_existing_node_id(nodes, target)
        edges[:] = [edge for edge in edges if not (self._edge_from(edge) == source_id and self._edge_to(edge) == target_id)]
        return []

    def _handle_insert_node_between(self, operation, nodes, edges, outputs, warnings):
        payload = operation.payload
        before = payload.get("before_node") or operation.target_ref
        after = payload.get("after_node")
        if before is None:
            warnings.append(f"insert_node_between skipped because before_node was missing for {operation.op_id}")
            return []
        before_id = self._resolve_existing_node_id(nodes, before)
        if after is None:
            outgoing = [edge for edge in edges if self._edge_from(edge) == before_id]
            after = self._edge_to(outgoing[0]) if outgoing else None
        inserted_id = self._resolve_created_node_id(nodes, payload.get("node_id") or f"{before_id}__inserted", payload)
        nodes.append({"id": inserted_id, "kind": payload.get("kind", "generic"), "metadata": deepcopy(payload)})
        if after:
            after_id = self._resolve_existing_node_id(nodes, after)
            edges[:] = [edge for edge in edges if not (self._edge_from(edge) == before_id and self._edge_to(edge) == after_id)]
            self._ensure_edge(edges, before_id, inserted_id)
            self._ensure_edge(edges, inserted_id, after_id)
        else:
            self._ensure_edge(edges, before_id, inserted_id)
        return [inserted_id]

    def _handle_define_output_binding(self, operation, nodes, edges, outputs, warnings):
        output_ref = operation.payload.get("output_ref") or operation.target_ref or "output.final"
        name = self._output_name_from_ref(output_ref)
        source = operation.payload.get("source") or operation.payload.get("value_ref") or operation.target_ref
        existing = self._find_output(outputs, name)
        payload = {"name": name, "source": source}
        if existing is None:
            outputs.append(payload)
        else:
            existing.update(payload)
        return []

    def _handle_remove_output_binding(self, operation, nodes, edges, outputs, warnings):
        output_ref = operation.payload.get("output_ref") or operation.target_ref
        name = self._output_name_from_ref(output_ref) if output_ref else None
        if name is None:
            warnings.append(f"remove_output_binding skipped because output_ref was missing for {operation.op_id}")
            return []
        outputs[:] = [output for output in outputs if output.get("name") != name]
        return []

    def _handle_move_output_binding(self, operation, nodes, edges, outputs, warnings):
        output_ref = operation.payload.get("output_ref") or operation.target_ref
        name = self._output_name_from_ref(output_ref) if output_ref else None
        if name is None:
            warnings.append(f"move_output_binding skipped because output_ref was missing for {operation.op_id}")
            return []
        output = self._find_output(outputs, name)
        if output is None:
            warnings.append(f"move_output_binding skipped because output '{name}' does not exist")
            return []
        if "source" in operation.payload:
            output["source"] = operation.payload["source"]
        return []

    def _handle_rename_node(self, operation, nodes, edges, outputs, warnings):
        node = self._resolve_node(nodes, operation.target_ref)
        old_id = self._node_id(node)
        new_id = operation.payload.get("new_name") or operation.payload.get("new_id")
        if not new_id:
            warnings.append(f"rename_node skipped because new_name/new_id was missing for {operation.op_id}")
            return []
        if self._try_resolve_node_id(nodes, new_id):
            raise ValueError(f"Cannot rename node '{old_id}' to '{new_id}' because the target id already exists")
        self._set_node_id(node, new_id)
        for edge in edges:
            if self._edge_from(edge) == old_id:
                self._set_edge_from(edge, new_id)
            if self._edge_to(edge) == old_id:
                self._set_edge_to(edge, new_id)
        for output in outputs:
            source = output.get("source")
            if isinstance(source, str):
                output["source"] = self._rewrite_reference(source, old_id, new_id)
        return []

    def _resolve_created_node_id(self, nodes: list[dict[str, Any]], requested_id: str, payload: dict[str, Any]) -> str:
        if payload.get("kind") == "review_gate" and self._try_resolve_node_id(nodes, requested_id):
            base = f"{requested_id}__review_gate"
        else:
            base = requested_id
        candidate = base
        counter = 1
        while self._try_resolve_node_id(nodes, candidate):
            counter += 1
            candidate = f"{base}_{counter}"
        return candidate

    def _resolve_node(self, nodes: list[dict[str, Any]], ref: str | None) -> dict[str, Any]:
        resolved_id = self._resolve_existing_node_id(nodes, ref)
        for node in nodes:
            if self._node_id(node) == resolved_id:
                return node
        raise ValueError(f"Unable to resolve node '{ref}'")

    def _resolve_existing_node_id(self, nodes: list[dict[str, Any]], ref: str | None) -> str:
        if ref is None:
            raise ValueError("Patch operation requires a node target_ref")
        matches: list[str] = []
        for node in nodes:
            node_id = self._node_id(node)
            label = node.get("label")
            if node_id == ref or label == ref:
                matches.append(node_id)
                continue
            if node_id and node_id.split(".")[-1] == ref:
                matches.append(node_id)
        unique = sorted(set(matches))
        if not unique:
            raise ValueError(f"Unknown node reference: {ref}")
        if len(unique) > 1:
            raise ValueError(f"Ambiguous node reference '{ref}': {unique}")
        return unique[0]

    def _try_resolve_node_id(self, nodes: list[dict[str, Any]], ref: str | None) -> str | None:
        if ref is None:
            return None
        try:
            return self._resolve_existing_node_id(nodes, ref)
        except ValueError:
            return None

    def _node_id(self, node: dict[str, Any]) -> str:
        return str(node.get("id") or node.get("node_id") or "")

    def _set_node_id(self, node: dict[str, Any], new_id: str) -> None:
        if "id" in node or "node_id" not in node:
            node["id"] = new_id
            node.pop("node_id", None)
        else:
            node["node_id"] = new_id

    def _edge_from(self, edge: dict[str, Any]) -> str:
        return str(edge.get("from") or edge.get("source") or "")

    def _edge_to(self, edge: dict[str, Any]) -> str:
        return str(edge.get("to") or edge.get("target") or "")

    def _set_edge_from(self, edge: dict[str, Any], value: str) -> None:
        if "from" in edge or "source" not in edge:
            edge["from"] = value
            edge.pop("source", None)
        else:
            edge["source"] = value

    def _set_edge_to(self, edge: dict[str, Any], value: str) -> None:
        if "to" in edge or "target" not in edge:
            edge["to"] = value
            edge.pop("target", None)
        else:
            edge["target"] = value

    def _ensure_edge(self, edges: list[dict[str, Any]], source: str, target: str) -> None:
        if any(self._edge_from(edge) == source and self._edge_to(edge) == target for edge in edges):
            return
        edges.append({"from": source, "to": target})

    def _reroute_outputs(self, outputs: list[dict[str, Any]], old_id: str, new_id: str) -> None:
        for output in outputs:
            source = output.get("source")
            if isinstance(source, str):
                output["source"] = self._rewrite_reference(source, old_id, new_id)

    def _rewrite_reference(self, value: str, old_id: str, new_id: str) -> str:
        patterns = [
            (rf"^node\.{re.escape(old_id)}\.", f"node.{new_id}."),
            (rf"^{re.escape(old_id)}\.", f"{new_id}."),
            (rf"^{re.escape(old_id)}$", new_id),
        ]
        rewritten = value
        for pattern, replacement in patterns:
            rewritten = re.sub(pattern, replacement, rewritten)
        return rewritten

    def _find_output(self, outputs: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
        for output in outputs:
            if output.get("name") == name:
                return output
        return None

    def _output_name_from_ref(self, output_ref: str) -> str:
        if "." in output_ref:
            return output_ref.split(".")[-1]
        return output_ref

    def _updated_entry(self, existing_entry: str | None, operations: tuple[PatchOperation, ...]) -> str | None:
        entry = existing_entry
        for operation in operations:
            if operation.op_type == "create_node" and entry is None:
                entry = operation.payload.get("node_id") or operation.target_ref
            if operation.op_type == "rename_node" and entry == operation.target_ref:
                entry = operation.payload.get("new_name") or operation.payload.get("new_id") or entry
            if operation.op_type == "delete_node" and entry == operation.target_ref:
                entry = None
        return entry

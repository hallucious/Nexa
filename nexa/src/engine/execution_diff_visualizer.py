class ExecutionDiffVisualizer:
    """
    Render ExecutionSnapshotDiffReport into a human-readable text report.
    """

    @staticmethod
    def render(diff_report):

        lines = []

        lines.append("Execution Diff Report")
        lines.append("=====================")
        lines.append("")

        # Added nodes
        if diff_report.added_nodes:
            lines.append("Nodes Added")
            lines.append("-----------")
            for node in diff_report.added_nodes:
                lines.append(node)
            lines.append("")

        # Removed nodes
        if diff_report.removed_nodes:
            lines.append("Nodes Removed")
            lines.append("-------------")
            for node in diff_report.removed_nodes:
                lines.append(node)
            lines.append("")

        # Modified nodes
        if diff_report.modified_nodes:
            lines.append("Nodes Modified")
            lines.append("--------------")

            for node in diff_report.modified_nodes:

                lines.append(node.node_id)

                if node.output_changed:
                    lines.append("  output changed")

                if node.artifact_changed:
                    lines.append("  artifact changed")

                if node.hash_changed:
                    lines.append("  hash mismatch")

                if node.metadata_changed:
                    lines.append("  metadata changed")

                if getattr(node, "verifier_changed", False):
                    lines.append("  verifier changed")

                lines.append("")

        # Summary
        summary = diff_report.summary

        lines.append("Summary")
        lines.append("-------")
        lines.append(f"nodes A: {summary['total_nodes_a']}")
        lines.append(f"nodes B: {summary['total_nodes_b']}")
        lines.append(f"added: {summary['added_count']}")
        lines.append(f"removed: {summary['removed_count']}")
        lines.append(f"modified: {summary['modified_count']}")
        if "verifier_changed_count" in summary:
            lines.append(f"verifier_changed: {summary['verifier_changed_count']}")

        return "\n".join(lines)
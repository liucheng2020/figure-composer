"""Figure provenance helpers for V19."""

import json
import os


SCHEMA_VERSION = "1.0"


def get_sidecar_path(figure_path):
    """Return the conventional sidecar path for a figure."""
    stem, _ = os.path.splitext(figure_path)
    return f"{stem}.provenance.json"


def load_figure_provenance(figure_path):
    """Load <figure_stem>.provenance.json when it exists."""
    sidecar_path = get_sidecar_path(figure_path)
    if not os.path.exists(sidecar_path):
        return None
    try:
        with open(sidecar_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    data["_provenance_path"] = sidecar_path
    return data


def _safe_relpath(path, root):
    """Return a stable relative path when possible."""
    if not path:
        return None
    if not root:
        return path
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def build_composition_provenance(base_path, canvas_name, layouts, project_root=None):
    """Build compact JSON linking each exported panel to its source code index."""
    panels = []
    for layout in layouts:
        pdf_info = layout.pdf_info
        source_path = getattr(pdf_info, "original_path", None) or pdf_info.filepath
        provenance = getattr(pdf_info, "provenance", None)
        best_match = provenance.get("best_match", {}) if isinstance(provenance, dict) else {}
        sidecar_path = provenance.get("_provenance_path") if isinstance(provenance, dict) else None
        panel = {
            "panel_label": layout.label,
            "figure_file": pdf_info.filename,
            "figure_path_rel": _safe_relpath(source_path, project_root),
            "provenance_path_rel": _safe_relpath(sidecar_path, project_root),
            "code_file": best_match.get("code_file"),
            "code_lines": best_match.get("code_lines"),
            "confidence": provenance.get("confidence") if isinstance(provenance, dict) else None,
            "provenance_status": "found" if provenance else "missing",
        }
        panels.append(panel)

    return {
        "schema_version": SCHEMA_VERSION,
        "provenance_type": "figure_composition_index",
        "composition": {
            "base_path": base_path,
            "canvas_name": canvas_name,
        },
        "panels": panels,
    }


def write_composition_provenance(base_path, canvas_name, layouts, project_root=None):
    """Write <base_path>_provenance.json and return its path."""
    manifest = build_composition_provenance(base_path, canvas_name, layouts, project_root)
    out_path = f"{base_path}_provenance.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return out_path

"""
project_io.py - V17 figbox container I/O

Self-contained .figbox project format. A .figbox file is a ZIP archive
that bundles the layout JSON together with copies of every original
asset, so the project can be reopened and re-rendered no matter what
happens to the source files (moved, renamed, deleted).

Container layout:
    my_figure.figbox  (ZIP, no compression for already-compressed PDFs)
    ├── manifest.json      container metadata
    ├── project.json       layout data with relative asset paths
    └── assets/            copies of every embedded source file
        ├── 01_xxx.pdf
        └── 02_xxx.pdf

Public API:
    pack_figbox(save_path, project_data, asset_filepaths) -> None
    unpack_figbox(load_path) -> (project_data, temp_dir)
    import_legacy_figproj(figproj_path) -> (project_data, temp_dir)
    cleanup_temp_dir(temp_dir) -> None
    is_figbox(path) -> bool
    get_autosave_dir() -> str
"""

import os
import json
import shutil
import tempfile
import zipfile
import hashlib
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

FIGBOX_FORMAT_VERSION = "1.0"
GENERATOR = "FigBox V19"
MANIFEST_NAME = "manifest.json"
PROJECT_NAME = "project.json"
ASSETS_DIR = "assets"
TEMP_PREFIX = "figbox_"
AUTOSAVE_DIR_NAME = "figbox_autosave"


def _short_hash(filepath):
    """Compute an 8-char content hash used for asset name de-duplication."""
    if not os.path.exists(filepath):
        return hashlib.md5(filepath.encode("utf-8")).hexdigest()[:8]
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        h.update(f.read(65536))
    return h.hexdigest()[:8]


def _resolve_asset_name(filepath, used_names):
    """Pick a unique arcname under assets/ for a source file."""
    base = os.path.basename(filepath)
    if base not in used_names:
        used_names.add(base)
        return base
    name, ext = os.path.splitext(base)
    suffix = _short_hash(filepath)
    candidate = f"{name}__{suffix}{ext}"
    n = 1
    while candidate in used_names:
        candidate = f"{name}__{suffix}_{n}{ext}"
        n += 1
    used_names.add(candidate)
    return candidate


def pack_figbox(save_path, project_data, asset_filepaths=None):
    """Pack project metadata + every referenced asset into a .figbox archive.

    The function rewrites layout.pdf_path entries from absolute filesystem
    paths to container-relative paths ("assets/<name>") and stores the
    original absolute path in layout.original_path for later "relink".

    Args:
        save_path: destination .figbox path
        project_data: dict with the same shape as the legacy figproj JSON
        asset_filepaths: optional list of extra source paths to embed even
            if they are not directly referenced in layouts (defensive)
    """
    save_path = str(save_path)

    used_names = set()
    path_to_arcname = {}
    embed_queue = []

    layouts = project_data.get("layouts", [])
    for layout in layouts:
        src = layout.get("pdf_path")
        if not src:
            continue
        abs_src = os.path.abspath(src)
        if abs_src in path_to_arcname:
            continue
        if not os.path.exists(abs_src):
            logger.warning("pack_figbox: source asset missing, will not embed: %s", abs_src)
            continue
        arcname = ASSETS_DIR + "/" + _resolve_asset_name(abs_src, used_names)
        path_to_arcname[abs_src] = arcname
        embed_queue.append((abs_src, arcname))

    for src in (asset_filepaths or []):
        if not src:
            continue
        abs_src = os.path.abspath(src)
        if abs_src in path_to_arcname:
            continue
        if not os.path.exists(abs_src):
            continue
        arcname = ASSETS_DIR + "/" + _resolve_asset_name(abs_src, used_names)
        path_to_arcname[abs_src] = arcname
        embed_queue.append((abs_src, arcname))

    new_project_data = json.loads(json.dumps(project_data))
    new_project_data["format_version"] = FIGBOX_FORMAT_VERSION

    # Drop transient runtime keys that should not be persisted
    for transient in ("_temp_dir", "_manifest", "_legacy_imported", "_missing_files"):
        new_project_data.pop(transient, None)

    for new_layout, old_layout in zip(new_project_data.get("layouts", []), layouts):
        src = old_layout.get("pdf_path")
        if src:
            abs_src = os.path.abspath(src)
            original_src = old_layout.get("original_path") or abs_src
            arcname = path_to_arcname.get(abs_src)
            if arcname:
                new_layout["pdf_path"] = arcname
                new_layout["original_path"] = original_src
                new_layout.pop("is_missing", None)
            else:
                new_layout["pdf_path"] = abs_src
                new_layout["original_path"] = original_src
                new_layout["is_missing"] = True
        exp = old_layout.get("expanded_filepath")
        if exp:
            abs_exp = os.path.abspath(exp)
            arcname = path_to_arcname.get(abs_exp)
            if arcname:
                new_layout["expanded_filepath"] = arcname
            else:
                # Boundary-expanded copies are derived; we don't keep stale absolute paths
                new_layout["expanded_filepath"] = None

    manifest = {
        "format": "figbox",
        "format_version": FIGBOX_FORMAT_VERSION,
        "generator": GENERATOR,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "asset_count": len(embed_queue),
    }

    tmp_path = save_path + ".tmp"
    try:
        # ZIP_STORED because PDFs and TIFs are already compressed; this
        # keeps packing fast and avoids CPU spent on entropy that won't shrink.
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
            zf.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
            zf.writestr(PROJECT_NAME, json.dumps(new_project_data, ensure_ascii=False, indent=2))
            for abs_src, arcname in embed_queue:
                zf.write(abs_src, arcname)
        os.replace(tmp_path, save_path)
        logger.info("pack_figbox: wrote %s (%d assets)", save_path, len(embed_queue))
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def unpack_figbox(load_path):
    """Extract a .figbox to a fresh temp dir and return (project_data, temp_dir).

    Layout pdf_path values are rewritten to absolute paths inside temp_dir,
    so the existing PDFInfo / LayoutItem objects can use them transparently.
    Caller is responsible for calling cleanup_temp_dir(temp_dir) eventually.
    """
    load_path = str(load_path)
    if not os.path.isfile(load_path):
        raise FileNotFoundError(load_path)

    temp_dir = tempfile.mkdtemp(prefix=TEMP_PREFIX)
    try:
        with zipfile.ZipFile(load_path, "r") as zf:
            names = zf.namelist()
            if MANIFEST_NAME not in names:
                raise ValueError(f"Invalid .figbox: missing {MANIFEST_NAME}")
            if PROJECT_NAME not in names:
                raise ValueError(f"Invalid .figbox: missing {PROJECT_NAME}")
            # Reject path-traversal entries before extracting
            for entry in names:
                norm = os.path.normpath(entry)
                if norm.startswith("..") or os.path.isabs(norm):
                    raise ValueError(f"Invalid .figbox: unsafe entry {entry}")
            zf.extractall(temp_dir)

        with open(os.path.join(temp_dir, MANIFEST_NAME), "r", encoding="utf-8") as f:
            manifest = json.load(f)
        with open(os.path.join(temp_dir, PROJECT_NAME), "r", encoding="utf-8") as f:
            project_data = json.load(f)

        for layout in project_data.get("layouts", []):
            pdf_path = layout.get("pdf_path", "")
            if pdf_path and not os.path.isabs(pdf_path):
                layout["pdf_path"] = os.path.join(temp_dir, pdf_path)
            exp_path = layout.get("expanded_filepath")
            if exp_path and not os.path.isabs(exp_path):
                layout["expanded_filepath"] = os.path.join(temp_dir, exp_path)

        project_data["_temp_dir"] = temp_dir
        project_data["_manifest"] = manifest
        logger.info("unpack_figbox: extracted %s -> %s", load_path, temp_dir)
        return project_data, temp_dir
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def import_legacy_figproj(figproj_path):
    """Load a legacy .figproj into in-memory project_data.

    Returns (project_data, temp_dir). For legacy projects there is nothing
    to extract, but we still create a temp_dir so the caller can use the
    same lifecycle as for a real .figbox. Missing originals are flagged
    (layout['is_missing'] = True) but kept in the layout list.
    """
    figproj_path = str(figproj_path)
    if not os.path.isfile(figproj_path):
        raise FileNotFoundError(figproj_path)

    with open(figproj_path, "r", encoding="utf-8") as f:
        project_data = json.load(f)

    missing = []
    for layout in project_data.get("layouts", []):
        pdf_path = layout.get("pdf_path", "")
        if pdf_path and not os.path.exists(pdf_path):
            layout["is_missing"] = True
            missing.append(pdf_path)

    temp_dir = tempfile.mkdtemp(prefix=TEMP_PREFIX + "legacy_")
    project_data["_temp_dir"] = temp_dir
    project_data["_legacy_imported"] = True
    project_data["_missing_files"] = missing
    logger.info("import_legacy_figproj: %s (%d missing)", figproj_path, len(missing))
    return project_data, temp_dir


def cleanup_temp_dir(temp_dir):
    """Safely remove a temp dir created by unpack_figbox / import_legacy_figproj."""
    if not temp_dir:
        return
    if not os.path.isdir(temp_dir):
        return
    # Refuse to delete anything that doesn't look like one of ours
    if not os.path.basename(temp_dir).startswith(TEMP_PREFIX):
        logger.warning("cleanup_temp_dir: refusing to remove non-figbox dir %s", temp_dir)
        return
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info("cleanup_temp_dir: removed %s", temp_dir)
    except Exception as e:
        logger.warning("cleanup_temp_dir failed: %s: %s", temp_dir, e)


def is_figbox(path):
    """True if path is an existing valid .figbox container."""
    if not path or not os.path.isfile(path):
        return False
    if not str(path).lower().endswith(".figbox"):
        return False
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            return MANIFEST_NAME in names and PROJECT_NAME in names
    except zipfile.BadZipFile:
        return False


def get_autosave_dir():
    """Return (and create) the autosave directory used by auto_backup.py."""
    base = os.path.join(tempfile.gettempdir(), AUTOSAVE_DIR_NAME)
    os.makedirs(base, exist_ok=True)
    return base

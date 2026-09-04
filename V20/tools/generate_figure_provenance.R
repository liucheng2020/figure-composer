# =============================================================================
# Script: generate_figure_provenance.R
# Purpose:
#   Recover provenance JSON for already-generated scientific figures by scanning
#   existing R/Python code. This is a conservative inference tool for old
#   projects; it does not claim that low-confidence matches are ground truth.
#
# Outputs:
#   1. <project_root>/figure_provenance/figure_provenance_manifest.json
#   2. One <figure_stem>.provenance.json sidecar next to each figure
#
# Usage:
#   Rscript generate_figure_provenance.R "D:/path/to/project"
#
# Notes:
#   - Requires jsonlite. This script does not install packages automatically.
#   - No generation time is recorded.
#   - Paths are written as both absolute and project-relative paths.
# =============================================================================

# ---- 0. Check required packages and parse project root -----------------------

if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("Package 'jsonlite' is required. Please install it before running this script.")
}

args <- commandArgs(trailingOnly = TRUE)

if (length(args) >= 1 && nzchar(args[1])) {
  project_root <- normalizePath(args[1], winslash = "/", mustWork = TRUE)
} else {
  project_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
}

out_dir <- file.path(project_root, "figure_provenance")
if (!dir.exists(out_dir)) {
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
}

schema_version <- "1.0"

# ---- 1. Define reusable helpers ---------------------------------------------

normalize_path_text <- function(path) {
  # Convert Windows backslashes to forward slashes so JSON is stable.
  gsub("\\\\", "/", path)
}

relative_to_project <- function(path) {
  # Store project-relative paths whenever possible; fall back to input path.
  normalized <- normalize_path_text(normalizePath(path, winslash = "/", mustWork = FALSE))
  root <- paste0(normalize_path_text(project_root), "/")
  sub(paste0("^", gsub("([\\^\\$\\.\\|\\?\\*\\+\\(\\)\\[\\]\\{\\}])", "\\\\\\1", root)), "", normalized)
}

is_ignored_path <- function(path) {
  # Exclude trash, git internals, virtual environments, build outputs, and this
  # script's own output directory to avoid self-matching generated JSON.
  normalized <- normalize_path_text(path)
  grepl("(^|/)(\\.Trash|\\.git|__pycache__|\\.pytest_cache|\\.venv|venv|env|build|dist|figure_provenance)(/|$)",
        normalized, ignore.case = TRUE)
}

json_null_if_empty <- function(x) {
  # Keep JSON fields explicit but compact.
  if (length(x) == 0) {
    return(NULL)
  }
  x
}

extract_r_packages <- function(lines) {
  # Extract packages from library(pkg), library("pkg"), require(pkg), require("pkg").
  pkg_lines <- grep("^\\s*(library|require)\\s*\\(", lines, value = TRUE)
  pkgs <- gsub("^\\s*(library|require)\\s*\\(\\s*['\"]?([^'\"\\),]+).*", "\\2", pkg_lines)
  unique(trimws(pkgs[nzchar(pkgs)]))
}

extract_python_packages <- function(lines) {
  # Extract top-level imports from Python scripts.
  import_lines <- grep("^\\s*(import|from)\\s+[A-Za-z0-9_\\.]+", lines, value = TRUE)
  pkgs <- gsub("^\\s*import\\s+([A-Za-z0-9_\\.]+).*", "\\1", import_lines)
  pkgs <- gsub("^\\s*from\\s+([A-Za-z0-9_\\.]+)\\s+import.*", "\\1", pkgs)
  pkgs <- sub("\\..*$", "", pkgs)
  unique(trimws(pkgs[nzchar(pkgs)]))
}

extract_object_names <- function(context_lines) {
  # Heuristic extraction of assigned object names near plotting code.
  # This is intentionally conservative and only records obvious assignments.
  assignment_lines <- grep("(<-|=)\\s*", context_lines, value = TRUE)
  left_side <- gsub("\\s*(<-|=).*", "", assignment_lines)
  objects <- grep("^[A-Za-z][A-Za-z0-9_\\.]*$", trimws(left_side), value = TRUE)
  unique(objects)
}

safe_read_lines <- function(path) {
  # Try UTF-8 first; fall back to system encoding if needed.
  lines <- tryCatch(
    readLines(path, warn = FALSE, encoding = "UTF-8"),
    error = function(e) character(0)
  )
  if (length(lines) == 0) {
    lines <- tryCatch(readLines(path, warn = FALSE), error = function(e) character(0))
  }
  lines
}

write_json_file <- function(object, path) {
  # Use null = "null" so missing fields remain JSON null instead of disappearing
  # unpredictably. auto_unbox keeps scalar fields readable.
  jsonlite::write_json(
    object,
    path,
    auto_unbox = TRUE,
    pretty = TRUE,
    na = "null",
    null = "null"
  )
}

# ---- 2. Define project-specific keyword dictionaries -------------------------

fig_exts <- c(".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg")

save_keywords <- c(
  "ggsave", "pdf(", "png(", "tiff(", "jpeg(", "bmp(", "svg(",
  "cairo_pdf(", "dev.copy", "ggplot2::ggsave", "grDevices::pdf",
  "grDevices::png", "CairoPDF", "savefig", ".savefig("
)

data_keywords <- c(
  "qs::qread", "qread(", "readRDS(", "read.csv(", "read.table(",
  "readxl::read_excel", "Seurat::Read10X", "LoadH5Seurat",
  "fread(", "vroom::vroom_read", "scanpy.read_h5ad", "sc.read_h5ad",
  "pandas.read_", "pd.read_"
)

plot_keywords <- c(
  "DimPlot", "FeaturePlot", "DotPlot", "VlnPlot", "DoHeatmap",
  "FindMarkers", "FindAllMarkers", "RunUMAP", "RunTSNE",
  "ggplot", "geom_", "enrichGO", "GSEA", "survfit", "ComplexHeatmap",
  "pheatmap", "Heatmap", "CellChat", "netVisual", "SCop", "GroupHeatmap",
  "ggforest", "ggvolcano", "corrplot", "visNetwork", "plt.", "sns."
)

# ---- 3. Collect figures and code files --------------------------------------

all_files <- list.files(project_root, recursive = TRUE, full.names = TRUE, all.files = FALSE)
all_files <- all_files[!vapply(all_files, is_ignored_path, logical(1))]

fig_pattern <- paste0("(", paste0(gsub("\\.", "\\\\.", fig_exts), collapse = "|"), ")$")
fig_files <- all_files[grepl(fig_pattern, all_files, ignore.case = TRUE)]

code_files <- all_files[grepl("\\.(R|Rmd|qmd|py)$", all_files, ignore.case = TRUE)]

cat("Project root:", project_root, "\n")
cat("Found", length(fig_files), "figure files\n")
cat("Found", length(code_files), "code files\n")

# ---- 4. Index code files -----------------------------------------------------

code_index <- vector("list", length(code_files))

for (i in seq_along(code_files)) {
  code_path <- code_files[i]
  lines <- safe_read_lines(code_path)
  if (length(lines) == 0) {
    next
  }

  extension <- tolower(tools::file_ext(code_path))
  packages <- if (extension == "py") extract_python_packages(lines) else extract_r_packages(lines)

  data_reads <- character(0)
  for (keyword in data_keywords) {
    hits <- grep(keyword, lines, value = TRUE, fixed = TRUE)
    if (length(hits) > 0) {
      data_reads <- c(data_reads, hits)
    }
  }

  code_index[[i]] <- list(
    path_abs = normalize_path_text(normalizePath(code_path, winslash = "/", mustWork = FALSE)),
    path_rel = relative_to_project(code_path),
    lines = lines,
    packages = packages,
    data_reads = unique(trimws(data_reads))
  )
}

code_index <- code_index[!vapply(code_index, is.null, logical(1))]

# ---- 5. Build a save-call index once -----------------------------------------

has_save_keyword <- function(text) {
  # Test whether a line or short context contains any figure-saving function.
  any(vapply(save_keywords, function(keyword) {
    grepl(keyword, text, fixed = TRUE)
  }, logical(1)))
}

build_save_call_index <- function() {
  # The slow version searched every code file for every figure. This index scans
  # every code file only once, keeps only save-call blocks, and then figures are
  # matched against this much smaller list.
  index <- list()

  for (entry in code_index) {
    lines <- entry$lines
    n <- length(lines)
    if (n == 0) {
      next
    }

    save_lines <- integer(0)
    for (keyword in save_keywords) {
      save_lines <- c(save_lines, grep(keyword, lines, fixed = TRUE))
    }
    save_lines <- sort(unique(save_lines))

    if (length(save_lines) == 0) {
      next
    }

    for (save_line in save_lines) {
      # Short context is used for matching filenames split across multi-line
      # save calls; long context is used for method/data provenance extraction.
      match_start <- max(1, save_line - 3)
      match_end <- min(n, save_line + 3)
      ctx_start <- max(1, save_line - 50)
      ctx_end <- min(n, save_line + 30)

      match_context <- paste(lines[match_start:match_end], collapse = "\n")
      ctx_lines <- lines[ctx_start:ctx_end]
      ctx_text <- paste(ctx_lines, collapse = "\n")

      found_plots <- plot_keywords[vapply(plot_keywords, function(keyword) {
        grepl(keyword, ctx_text, fixed = TRUE)
      }, logical(1))]

      local_data <- entry$data_reads
      for (keyword in data_keywords) {
        local_hits <- grep(keyword, ctx_lines, value = TRUE, fixed = TRUE)
        if (length(local_hits) > 0) {
          local_data <- c(local_data, local_hits)
        }
      }

      compact_input_data <- unique(trimws(local_data))
      if (length(compact_input_data) > 5) {
        compact_input_data <- compact_input_data[seq_len(5)]
      }

      index[[length(index) + 1]] <- list(
        code_file = entry$path_rel,
        code_lines = c(ctx_start, ctx_end),
        save_line = save_line,
        save_call = trimws(lines[save_line]),
        match_context = match_context,
        match_context_norm = normalize_path_text(match_context),
        plot_calls = unique(found_plots),
        input_data = compact_input_data
      )
    }
  }

  index
}

save_call_index <- build_save_call_index()
cat("Indexed", length(save_call_index), "figure save-call blocks\n")

# ---- 6. Match figures to indexed save calls ----------------------------------

find_filename_in_code <- function(figure_path) {
  basename_fig <- basename(figure_path)
  rel_fig_path <- relative_to_project(figure_path)
  escaped_basename <- gsub("([\\^\\$\\.\\|\\?\\*\\+\\(\\)\\[\\]\\{\\}])", "\\\\\\1", basename_fig)
  escaped_rel <- gsub("([\\^\\$\\.\\|\\?\\*\\+\\(\\)\\[\\]\\{\\}])", "\\\\\\1", rel_fig_path)
  matches <- list()

  for (entry in save_call_index) {
    is_match <- grepl(basename_fig, entry$match_context, fixed = TRUE) ||
      grepl(rel_fig_path, entry$match_context_norm, fixed = TRUE) ||
      grepl(escaped_basename, entry$match_context, perl = TRUE) ||
      grepl(escaped_rel, entry$match_context_norm, perl = TRUE)

    if (!is_match) {
      next
    }

    exact_filename_in_save_call <- grepl(basename_fig, entry$save_call, fixed = TRUE)
    exact_path_in_save_call <- grepl(rel_fig_path, normalize_path_text(entry$save_call), fixed = TRUE)
    dynamic_filename <- grepl("paste0|paste\\(|file\\.path|sprintf|glue\\(", entry$save_call)

    matches[[length(matches) + 1]] <- list(
      code_file = entry$code_file,
      code_lines = entry$code_lines,
      save_line = entry$save_line,
      save_call = entry$save_call,
      plot_calls = entry$plot_calls,
      input_data = entry$input_data,
      exact = exact_filename_in_save_call || exact_path_in_save_call,
      dynamic = dynamic_filename
    )
  }

  matches
}

guess_script_from_dir <- function(figure_path) {
  figure_dir <- dirname(figure_path)
  candidates <- character(0)

  for (depth in 1:4) {
    check_dir <- figure_dir
    if (depth > 1) {
      for (unused in seq_len(depth - 1)) {
        check_dir <- dirname(check_dir)
      }
    }
    if (!dir.exists(check_dir)) {
      next
    }
    r_scripts <- list.files(check_dir, pattern = "\\.(R|Rmd|qmd)$", full.names = TRUE, recursive = FALSE, ignore.case = TRUE)
    py_scripts <- list.files(check_dir, pattern = "\\.py$", full.names = TRUE, recursive = FALSE, ignore.case = TRUE)
    candidates <- c(candidates, r_scripts, py_scripts)
  }

  unique(vapply(candidates, relative_to_project, character(1)))
}

build_record_for_figure <- function(figure_path) {
  figure_abs <- normalize_path_text(normalizePath(figure_path, winslash = "/", mustWork = FALSE))
  figure_rel <- relative_to_project(figure_path)
  figure_file <- basename(figure_path)
  matches <- find_filename_in_code(figure_path)

  if (length(matches) == 0) {
    dir_candidates <- guess_script_from_dir(figure_path)
    best_match <- list(
      code_file = if (length(dir_candidates) > 0) dir_candidates[1] else NULL,
      code_lines = NULL,
      save_line = NULL,
      save_call = NULL,
      plot_calls = list(),
      input_data = list()
    )
    candidate_matches <- lapply(dir_candidates, function(candidate) {
      list(
        code_file = candidate,
        code_lines = NULL,
        reason = "Nearby script candidate; no exact save call found"
      )
    })
    confidence <- "low"
    match_method <- "nearby_script"
    needs_manual_review <- TRUE
    evidence <- list(
      paste0("No exact save call found for filename: ", figure_file),
      paste0("Figure path: ", figure_rel)
    )
    unresolved_questions <- list(
      "Could not find an exact save call referencing this filename",
      "Manual verification is recommended before report writing"
    )
  } else {
    exact_matches <- matches[vapply(matches, function(match) isTRUE(match$exact), logical(1))]
    dynamic_matches <- matches[vapply(matches, function(match) isTRUE(match$dynamic) && !isTRUE(match$exact), logical(1))]
    other_matches <- matches[vapply(matches, function(match) !isTRUE(match$exact) && !isTRUE(match$dynamic), logical(1))]
    ordered_matches <- c(exact_matches, dynamic_matches, other_matches)
    best <- ordered_matches[[1]]

    if (isTRUE(best$exact)) {
      confidence <- "high"
      match_method <- "exact_save_call"
      needs_manual_review <- FALSE
    } else if (isTRUE(best$dynamic)) {
      confidence <- "medium"
      match_method <- "dynamic_save_call"
      needs_manual_review <- TRUE
    } else {
      confidence <- "medium"
      match_method <- "contextual_save_call"
      needs_manual_review <- TRUE
    }

    best_match <- list(
      code_file = best$code_file,
      code_lines = best$code_lines,
      save_call = best$save_call,
      plot_calls = json_null_if_empty(best$plot_calls),
      input_data = json_null_if_empty(best$input_data)
    )

    remaining <- if (length(ordered_matches) > 1) ordered_matches[-1] else list()
    candidate_matches <- lapply(remaining, function(match) {
      list(
        code_file = match$code_file,
        code_lines = match$code_lines,
        reason = if (isTRUE(match$exact)) "Exact filename match in save call" else "Partial or contextual save-call match"
      )
    })

    evidence <- list(
      paste0("Save call at line ", best$save_line, ": ", best$save_call),
      paste0("Matched figure filename: ", figure_file),
      paste0("Matched code file: ", best$code_file)
    )
    if (length(best$plot_calls) > 0) {
      evidence <- c(evidence, paste0("Nearby plot functions: ", paste(best$plot_calls, collapse = ", ")))
    }
    unresolved_questions <- if (confidence == "high") list() else list(
      "Filename may be constructed dynamically or matched contextually; verify before final reporting"
    )
  }

  list(
    schema_version = schema_version,
    provenance_type = "figure_code_index",
    figure_file = figure_file,
    figure_path_rel = figure_rel,
    match_method = match_method,
    confidence = confidence,
    needs_manual_review = needs_manual_review,
    best_match = best_match
  ) |>
    (\(record) {
      if (confidence != "high" && length(candidate_matches) > 0) {
        record$candidate_matches <- candidate_matches
      }
      if (confidence == "low" || isTRUE(needs_manual_review)) {
        record$unresolved_questions <- unresolved_questions
      }
      record
    })()
}

# ---- 6. Build records and write sidecars ------------------------------------

figures_out <- vector("list", length(fig_files))
stats <- c(high = 0L, medium = 0L, low = 0L)

for (i in seq_along(fig_files)) {
  figure_path <- fig_files[i]
  record <- build_record_for_figure(figure_path)
  figures_out[[i]] <- record
  stats[record$confidence] <- stats[record$confidence] + 1L

  sidecar_path <- file.path(dirname(figure_path), paste0(tools::file_path_sans_ext(basename(figure_path)), ".provenance.json"))
  write_json_file(record, sidecar_path)

  if (i %% 100 == 0) {
    cat("Processed", i, "/", length(fig_files), "\n")
  }
}

cat("\nConfidence summary: high=", stats["high"],
    " medium=", stats["medium"],
    " low=", stats["low"], "\n")

# ---- 7. Write project-level manifest ----------------------------------------

git_commit <- tryCatch(
  {
    old_wd <- getwd()
    setwd(project_root)
    on.exit(setwd(old_wd), add = TRUE)
    commit <- system("git rev-parse HEAD", intern = TRUE, ignore.stderr = TRUE)
    if (length(commit) == 1 && nzchar(commit)) commit else NULL
  },
  error = function(e) NULL
)

manifest <- list(
  project = list(
    root = project_root,
    git_commit = git_commit,
    notes = paste0(
      "Figure provenance inferred from existing R/Python code. ",
      "Total figures: ", length(fig_files),
      ". high=", stats["high"],
      ", medium=", stats["medium"],
      ", low=", stats["low"],
      ". No generation time is recorded."
    )
  ),
  figures = figures_out
)

manifest_path <- file.path(out_dir, "figure_provenance_manifest.json")
write_json_file(manifest, manifest_path)

cat("Manifest written to:", manifest_path, "\n")
cat("Sidecar JSON files written next to each figure.\n")

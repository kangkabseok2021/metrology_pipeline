#!/usr/bin/env Rscript
# MetaboPipe R statistics orchestrator
# Usage: Rscript run_analysis.R <feature_matrix.csv> <metadata.csv> [out_dir]

suppressPackageStartupMessages({
  library(readr)
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript run_analysis.R <feature_matrix.csv> <metadata.csv> [out_dir]")
}

feature_csv  <- args[1]
metadata_csv <- args[2]
out_dir      <- if (length(args) >= 3) args[3] else "results"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# Source analysis modules relative to this script
script_dir <- tryCatch(
  dirname(sys.frame(1)$ofile),
  error = function(e) "."
)
source(file.path(script_dir, "pca.R"))
source(file.path(script_dir, "plsda.R"))
source(file.path(script_dir, "univariate.R"))

feat_mat <- readr::read_csv(feature_csv, show_col_types = FALSE)
metadata <- readr::read_csv(metadata_csv, show_col_types = FALSE)

message("[MetaboPipe] Running PCA...")
run_pca(feat_mat, metadata, out_dir)

message("[MetaboPipe] Running PLS-DA...")
run_plsda(feat_mat, metadata, out_dir)

message("[MetaboPipe] Running univariate statistics...")
run_univariate(feat_mat, metadata, out_dir)

message("[MetaboPipe] R statistics complete. Results written to: ", out_dir)

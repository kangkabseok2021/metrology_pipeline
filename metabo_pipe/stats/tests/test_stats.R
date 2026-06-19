library(testthat)
library(readr)
library(ggplot2)

# Source the analysis modules
script_dir <- tryCatch(dirname(sys.frame(1)$ofile), error = function(e) ".")
source(file.path(script_dir, "..", "pca.R"))
source(file.path(script_dir, "..", "univariate.R"))

# ---------------------------------------------------------------------------
# Synthetic test data: 10 samples (5 control, 5 treatment), 20 features
# Feature 1 is strongly elevated in treatment group
# ---------------------------------------------------------------------------

set.seed(42)
n_samples <- 10
n_features <- 20
feature_names <- paste0("feat_", seq_len(n_features))
sample_ids <- paste0("S", seq_len(n_samples))
groups <- c(rep("control", 5), rep("treatment", 5))

mat <- matrix(rnorm(n_samples * n_features, mean = 100, sd = 10), nrow = n_samples)
# Inject strong signal in feature 1 for treatment group
mat[6:10, 1] <- mat[6:10, 1] + 200

feat_df <- as.data.frame(mat)
colnames(feat_df) <- feature_names
feat_df <- cbind(sample_id = sample_ids, feat_df)

meta_df <- data.frame(sample_id = sample_ids, sample_group = groups)

# ---------------------------------------------------------------------------
# PCA tests
# ---------------------------------------------------------------------------

test_that("PCA runs without error", {
  tmp <- tempdir()
  result <- run_pca(feat_df, meta_df, tmp)
  expect_true(file.exists(file.path(tmp, "pca_scores.csv")))
  expect_true(file.exists(file.path(tmp, "pca_variance.csv")))
})

test_that("PCA variance proportions are non-negative and sum to 1", {
  tmp <- tempdir()
  result <- run_pca(feat_df, meta_df, tmp)
  var_file <- readr::read_csv(file.path(tmp, "pca_variance.csv"), show_col_types = FALSE)
  expect_true(all(var_file$variance_explained >= 0))
  expect_equal(sum(var_file$variance_explained), 1.0, tolerance = 1e-6)
})

test_that("PCA score file has expected columns", {
  tmp <- tempdir()
  run_pca(feat_df, meta_df, tmp)
  scores <- readr::read_csv(file.path(tmp, "pca_scores.csv"), show_col_types = FALSE)
  expect_true("PC1" %in% colnames(scores))
  expect_true("sample_id" %in% colnames(scores))
  expect_true("sample_group" %in% colnames(scores))
})

test_that("PCA returns one row per sample", {
  tmp <- tempdir()
  result <- run_pca(feat_df, meta_df, tmp)
  scores <- readr::read_csv(file.path(tmp, "pca_scores.csv"), show_col_types = FALSE)
  expect_equal(nrow(scores), n_samples)
})

# ---------------------------------------------------------------------------
# Univariate tests
# ---------------------------------------------------------------------------

test_that("Univariate analysis writes results file", {
  tmp <- tempdir()
  run_univariate(feat_df, meta_df, tmp)
  expect_true(file.exists(file.path(tmp, "univariate_results.csv")))
})

test_that("Univariate results have required columns", {
  tmp <- tempdir()
  run_univariate(feat_df, meta_df, tmp)
  res <- readr::read_csv(file.path(tmp, "univariate_results.csv"), show_col_types = FALSE)
  for (col in c("feature", "log2fc", "raw_p", "adj_p", "significant")) {
    expect_true(col %in% colnames(res), info = paste("Missing column:", col))
  }
})

test_that("BH-adjusted p-values are <= raw p-values on average", {
  tmp <- tempdir()
  run_univariate(feat_df, meta_df, tmp)
  res <- readr::read_csv(file.path(tmp, "univariate_results.csv"), show_col_types = FALSE)
  expect_true(mean(res$adj_p) >= mean(res$raw_p))
})

test_that("Injected signal in feature 1 is significant", {
  tmp <- tempdir()
  run_univariate(feat_df, meta_df, tmp)
  res <- readr::read_csv(file.path(tmp, "univariate_results.csv"), show_col_types = FALSE)
  feat1 <- res[res$feature == "feat_1", ]
  expect_true(feat1$significant)
})

test_that("Volcano plot is written for two-group comparison", {
  tmp <- tempdir()
  run_univariate(feat_df, meta_df, tmp)
  expect_true(file.exists(file.path(tmp, "volcano.png")))
})

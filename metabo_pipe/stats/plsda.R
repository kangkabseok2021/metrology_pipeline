run_plsda <- function(feat_mat, metadata, out_dir) {
  if (!requireNamespace("mixOmics", quietly = TRUE)) {
    message("mixOmics not available — skipping PLS-DA")
    return(invisible(NULL))
  }

  sample_col <- feat_mat[[1]]
  X <- as.matrix(feat_mat[, -1])
  rownames(X) <- sample_col

  meta_ordered <- metadata[match(sample_col, metadata$sample_id), ]
  Y <- factor(meta_ordered$sample_group)

  n_comp <- min(2L, nlevels(Y) - 1L, ncol(X))
  if (n_comp < 1L) {
    message("Not enough groups for PLS-DA")
    return(invisible(NULL))
  }

  model <- mixOmics::plsda(log1p(X), Y, ncomp = n_comp)

  scores_df <- as.data.frame(model$variates$X)
  scores_df$sample_id <- sample_col
  scores_df$sample_group <- as.character(Y)
  readr::write_csv(scores_df, file.path(out_dir, "plsda_scores.csv"))

  # VIP scores from component 1
  vip <- mixOmics::vip(model)
  vip_df <- data.frame(feature = rownames(vip), vip_comp1 = vip[, 1])
  vip_df <- vip_df[order(-vip_df$vip_comp1), ]
  readr::write_csv(vip_df, file.path(out_dir, "vip_scores.csv"))

  invisible(list(model = model, vip = vip_df))
}

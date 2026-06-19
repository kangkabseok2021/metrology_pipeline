run_pca <- function(feat_mat, metadata, out_dir) {
  sample_col <- feat_mat[[1]]
  X <- as.matrix(feat_mat[, -1])
  rownames(X) <- sample_col

  X_log <- log1p(X)
  X_scaled <- scale(X_log)

  pca <- stats::prcomp(X_scaled, center = FALSE, scale. = FALSE)
  var_exp <- pca$sdev^2 / sum(pca$sdev^2)

  scores <- as.data.frame(pca$x[, 1:min(2, ncol(pca$x))])
  scores$sample_id <- rownames(scores)
  scores <- merge(scores, metadata[, c("sample_id", "sample_group")],
                  by = "sample_id", all.x = TRUE)

  readr::write_csv(scores, file.path(out_dir, "pca_scores.csv"))
  readr::write_csv(
    data.frame(PC = paste0("PC", seq_along(var_exp)), variance_explained = var_exp),
    file.path(out_dir, "pca_variance.csv")
  )

  p <- ggplot2::ggplot(scores, ggplot2::aes(x = PC1, y = PC2, colour = sample_group)) +
    ggplot2::geom_point(size = 3) +
    ggplot2::theme_bw() +
    ggplot2::labs(title = "PCA Score Plot",
                  x = sprintf("PC1 (%.1f%%)", var_exp[1] * 100),
                  y = sprintf("PC2 (%.1f%%)", var_exp[2] * 100))
  ggplot2::ggsave(file.path(out_dir, "pca_scores.png"), p, width = 7, height = 5, dpi = 150)

  invisible(list(pca = pca, var_exp = var_exp, scores = scores))
}

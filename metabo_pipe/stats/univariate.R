run_univariate <- function(feat_mat, metadata, out_dir) {
  sample_col <- feat_mat[[1]]
  X <- as.matrix(feat_mat[, -1])
  rownames(X) <- sample_col

  meta_ordered <- metadata[match(sample_col, metadata$sample_id), ]
  groups <- factor(meta_ordered$sample_group)
  feature_names <- colnames(X)
  n_features <- length(feature_names)
  n_groups <- nlevels(groups)

  raw_p <- numeric(n_features)
  log2fc <- numeric(n_features)

  if (n_groups == 2) {
    lvls <- levels(groups)
    for (i in seq_len(n_features)) {
      g1 <- log1p(X[groups == lvls[1], i])
      g2 <- log1p(X[groups == lvls[2], i])
      if (stats::var(c(g1, g2)) == 0) {
        raw_p[i] <- 1.0
        log2fc[i] <- 0.0
        next
      }
      tt <- tryCatch(stats::t.test(g1, g2, var.equal = FALSE), error = function(e) list(p.value = 1.0))
      raw_p[i] <- tt$p.value
      log2fc[i] <- mean(g2) - mean(g1)
    }
  } else {
    for (i in seq_len(n_features)) {
      vals <- log1p(X[, i])
      df_aov <- data.frame(y = vals, g = groups)
      fit <- tryCatch(stats::aov(y ~ g, data = df_aov), error = function(e) NULL)
      raw_p[i] <- if (is.null(fit)) 1.0 else summary(fit)[[1]][["Pr(>F)"]][1]
    }
  }

  adj_p <- stats::p.adjust(raw_p, method = "BH")

  results <- data.frame(
    feature = feature_names,
    log2fc = log2fc,
    raw_p = raw_p,
    adj_p = adj_p,
    significant = adj_p < 0.05
  )
  readr::write_csv(results, file.path(out_dir, "univariate_results.csv"))

  # Volcano plot (two-group only)
  if (n_groups == 2) {
    results$neg_log10_p <- -log10(pmax(results$adj_p, 1e-300))
    p <- ggplot2::ggplot(
      results,
      ggplot2::aes(x = log2fc, y = neg_log10_p, colour = significant)
    ) +
      ggplot2::geom_point(alpha = 0.7) +
      ggplot2::scale_colour_manual(values = c("FALSE" = "grey60", "TRUE" = "#e74c3c")) +
      ggplot2::geom_hline(yintercept = -log10(0.05), linetype = "dashed") +
      ggplot2::theme_bw() +
      ggplot2::labs(title = "Volcano Plot", x = "log2 fold-change", y = "-log10(BH-FDR)")
    ggplot2::ggsave(file.path(out_dir, "volcano.png"), p, width = 7, height = 5, dpi = 150)
  }

  # Heatmap of significant features
  sig_features <- results$feature[results$significant]
  if (length(sig_features) >= 2 && requireNamespace("pheatmap", quietly = TRUE)) {
    heat_mat <- t(scale(log1p(X[, sig_features, drop = FALSE])))
    pheatmap::pheatmap(heat_mat,
                       annotation_col = data.frame(group = groups, row.names = sample_col),
                       filename = file.path(out_dir, "heatmap.png"),
                       width = 8, height = 6)
  }

  invisible(results)
}

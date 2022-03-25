#
# subsetIds subsets a seurat object with the cell ids
#
subsetIds <- function(scdata, cells_id) {
  meta_data_subset <- scdata@meta.data[match(cells_id, scdata@meta.data$cells_id), ]
  current_cells <- rownames(meta_data_subset)
  scdata <- subset(scdata, cells = current_cells)
  return(scdata)
}

sendCellsetToApi <- function(new_cell_set, api_url, experiment_id, cell_set_key, auth_JWT) {
  httr_query <- paste0('$[?(@.key == "', cell_set_key, '")]')
  children <- list(list("$insert" = list(index = "-", value = new_cell_set)))

  httr::PATCH(
    paste0(api_url, "/v1/experiments/", experiment_id, "/cellSets"),
    body = list(
      list("$match" = list(
        query = httr_query,
        value = list("children" = children)
      ))
    ),
    encode = "json",
    httr::add_headers(
      "Content-Type" = "application/boschni-json-merger+json",
      "Authorization" = auth_JWT
    )
  )
}
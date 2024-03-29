% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/utilities.R
\name{updateCellSetsThroughApi}
\alias{updateCellSetsThroughApi}
\title{Update the cell sets through the API}
\usage{
updateCellSetsThroughApi(
  cell_sets_object,
  api_url,
  experiment_id,
  cell_set_key,
  auth_JWT,
  append = TRUE
)
}
\arguments{
\item{cell_sets_object}{list of cellsets to patch}

\item{api_url}{character - api endpoint url}

\item{experiment_id}{character}

\item{cell_set_key}{character}

\item{auth_JWT}{character}
}
\description{
Used when re-clustering, cell sets are replaced.
Used after ScType, cell sets are added.
}

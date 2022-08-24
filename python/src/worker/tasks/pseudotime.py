import json

import backoff
import requests
from aws_xray_sdk.core import xray_recorder
from exceptions import raise_if_error

from ..config import config
from ..helpers.s3 import get_embedding
from ..result import Result
from . import Task


class GetPseudoTime(Task):
    def __init__(self, msg):
        super().__init__(msg)
        self.experiment_id = config.EXPERIMENT_ID

    def _format_result(self, result):
        return Result(result["data"])

    def _format_request(self):

        embedding_etag = self.task_def["embedding"]["ETag"]
        embedding = get_embedding(embedding_etag)

        request = {
            "embedding": embedding,
            "embedding_settings": {
                "method": self.task_def["embedding"]["method"],
            },
            "clustering_settings": {
                "method": self.task_def["clustering"]["method"],
                "resolution": self.task_def["clustering"]["resolution"],
            },
            "root_nodes": self.task_def["rootNodes"]
        }

        return request

    @xray_recorder.capture("GetTrajectoryGraph.compute")
    @backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=30
    )
    def compute(self):
        request = self._format_request()

        r = requests.post(
            f"{config.R_WORKER_URL}/v0/runPseudoTimeTask",
            headers={"content-type": "application/json"},
            data=json.dumps(request),
        )

        # raise an exception if an HTTPError occurred. otherwise r.json() will fail
        r.raise_for_status()
        # The index order relies on cells_id in an ascending form. The order is made in the R part.
        result = r.json()
        raise_if_error(result)

        return self._format_result(result)

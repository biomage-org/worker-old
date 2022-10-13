import gzip
import io
import json
from unittest import TestCase

import boto3
import mock
import pytest
import responses
from botocore.stub import Stubber
from exceptions import RWorkerException
from tests.data.embedding import mock_embedding
from worker.config import config
from worker.tasks.trajectory_analysis_starting_nodes import GetTrajectoryAnalysisStartingNodes

mock_embedding_etag = "mockEmbeddingETag"


class TestTrajectoryAnalysisStartingNodes:
    @pytest.fixture(autouse=True)
    def load_correct_definition(self):
        self.correct_request = {
            "body": {
                "name": "GetTrajectoryAnalysisStartingNodes",
                "embedding": {
                  "ETag": mock_embedding_etag,
                  "method": "umap",
                  "methodSettings": {
                    "distanceMetric": "cosine",
                    "minimumDistance": 0.3
                  }
                },
                "clustering": {"method": "louvain", "resolution": 0.8},
            }
        }

    def get_s3_stub(self):
        s3 = boto3.client("s3", **config.BOTO_RESOURCE_KWARGS)
        response = {
            "ContentLength": 10,
            "ContentType": "utf-8",
            "ResponseMetadata": {
                "Bucket": config.RESULTS_BUCKET,
            },
        }

        expected_params = {
            "Bucket": config.RESULTS_BUCKET,
            "Key": mock_embedding_etag,
        }
        stubber = Stubber(s3)
        stubber.add_response("head_object", response, expected_params)

        # Get object
        content_string = json.dumps(mock_embedding).encode("utf-8")
        content_bytes = gzip.compress(content_string)
        data = io.BytesIO()
        data.write(content_bytes)
        data.seek(0)

        response = {
            "ContentLength": len(content_bytes),
            "ContentType": "application/gzip",
            "Body": data,
            "ResponseMetadata": {
                "Bucket": config.RESULTS_BUCKET,
            },
        }
        stubber.add_response("get_object", response, expected_params)
        return (stubber, s3)

    def test_throws_on_missing_parameters(self):
        with pytest.raises(TypeError):
            GetTrajectoryAnalysisStartingNodes()

    def test_throws_on_invalid_task_def(self):
        with pytest.raises(Exception):
            GetTrajectoryAnalysisStartingNodes(self).compute("invalid input")

    @responses.activate
    def test_works_with_correct_request(self):

        worker_payload = {
            "data": {
                "nodes": {
                    "Y_1": {
                        "connected_nodes": ["Y_2"],
                        "node_id": "Y_1",
                        "x": 7.5735,
                        "y": 6.3022,
                    },
                    "Y_2": {
                        "connected_nodes": ["Y_3"],
                        "node_id": "Y_2",
                        "x": 11.5128,
                        "y": 7.8589,
                    },
                    "Y_3": {
                        "connected_nodes": [],
                        "node_id": "Y_3",
                        "x": 9.1538,
                        "y": 6.6533,
                    },
                }
            }
        }

        stubber, s3 = self.get_s3_stub()

        with mock.patch("boto3.client") as n, stubber:
            n.return_value = s3

            responses.add(
                responses.POST,
                f"{config.R_WORKER_URL}/v0/runTrajectoryAnalysisStartingNodesTask",
                json=worker_payload,
                status=200,
            )

            result = GetTrajectoryAnalysisStartingNodes(self.correct_request).compute()

            TestCase().assertDictEqual(result.data, worker_payload["data"])
            stubber.assert_no_pending_responses()

    @responses.activate
    def test_should_throw_exception_on_r_worker_error(self):

        error_code = "MOCK_R_WORKER_ERROR"
        user_message = "Some worker error"
        error_payload = {
            "error": {"error_code": error_code, "user_message": user_message}
        }

        stubber, s3 = self.get_s3_stub()

        with mock.patch("boto3.client") as n, stubber:
            n.return_value = s3

            responses.add(
                responses.POST,
                f"{config.R_WORKER_URL}/v0/runTrajectoryAnalysisStartingNodesTask",
                json=error_payload,
                status=200,
            )

            with pytest.raises(RWorkerException) as exception_info:
                GetTrajectoryAnalysisStartingNodes(self.correct_request).compute()

            assert exception_info.value.args[0] == error_code
            assert exception_info.value.args[1] == user_message

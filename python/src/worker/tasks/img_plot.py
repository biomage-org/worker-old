import json

import backoff
import requests
from aws_xray_sdk.core import xray_recorder
from exceptions import raise_if_error

from ..config import config
from ..result import Result
from ..tasks import Task

import PIL
from PIL import Image
import numpy as np

import boto3
s3 = boto3.client("s3", **config.BOTO_RESOURCE_KWARGS)

class GetImgPlot(Task):
    def __init__(self, msg):
        super().__init__(msg)
        self.task_etag = msg["ETag"]

    def _format_result(self, result):
        # Return a list of formatted results.
        return Result(result, upload=False)

    def _format_request(self):
        request = {
            "plotType": self.task_def["type"],
            "genes": self.task_def["features"],
            "etag": self.task_etag,
            "plotSubType": self.task_def["plotSubType"],
        }
        return request

    def _generate_img(self, pixels):
        rmat, gmat, bmat, amat = pixels
        formatted_pixels = []
        for rrow, grow, brow, arow in zip(rmat, gmat, bmat, amat):
            formatted_row = [(r, g, b, a) for r, g, b, a in zip(rrow, grow, brow, arow)]
            formatted_pixels.append(formatted_row)

        ready = np.array(formatted_pixels, dtype=np.uint8)
        img = Image.fromarray(ready, 'RGBA')

        img.save('img.png')
        s3.upload_file(
            Filename = './img.png',
            Bucket = 'worker-results-development-000000000000',
            Key = 'img.png'
        )

    @xray_recorder.capture("GetImgPlot.compute")
    @backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=30
    )
    def compute(self):
        request = self._format_request()
        response = requests.post(
            f"{config.R_WORKER_URL}/v0/getImgPlot",
            headers={"content-type": "application/json"},
            data=json.dumps(request),
        )

        response.raise_for_status()
        result = response.json()
        raise_if_error(result)
        raw_data = result.get("data")
        obj = json.loads(raw_data)
        
        data = obj['data']
        
        self._generate_img(data)


        # with open('raw-pixels.txt', 'w') as f:
        #     f.write(data)

        # s3.upload_file(
        #     Filename = './raw-pixels.txt',
        #     Bucket = 'worker-results-development-000000000000',
        #     Key = 'raw-pixels.txt'
        # )

        return self._format_result(data)

import json

import backoff
import numpy as np
import requests
from aws_xray_sdk.core import xray_recorder

from ..config import config
from ..result import Result
from ..tasks import Task


class GeneExpression(Task):
    def _format_result(self, result):
        # JSONify result.
        result = json.dumps(result)
        # Return a list of formatted results.
        return [Result(result)]

    @xray_recorder.capture("GeneExpression.compute")
    @backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=120
    )
    def compute(self):
        # the genes to get expression data for
        genes = self.task_def["genes"]
        # whether to perform feature scaling (defaults to True)
        # In r we currently use the data matrix of the Seurat object.
        # scale = self.task_def.get("scale", True)
        request = {"genes": genes}
        r = requests.post(
            f"{config.R_WORKER_URL}/v0/runExpression",
            headers={"content-type": "application/json"},
            data=json.dumps(request),
        )
        # raise an exception if an HTTPError if one occurred because otherwise r.json() will fail
        r.raise_for_status()
        resultR = r.json()
        truncatedR = resultR["truncatedExpression"]
        resultR = resultR["rawExpression"]
        result = {}
        if not len(resultR):
            result[genes[0]] = {
                "error": 404,
                "message": "Gene {} not found!".format(genes[0]),
            }

        else:
            for gene in resultR.keys():

                view = resultR[gene]
                # can't do summary stats on list with None's
                # casting to np array replaces None with np.nan
                viewnp = np.array(view, dtype=np.float)
                # This is not necessary and is also costly, but I leave it commented as a reminder
                # that this object has integer zeros and floating point for n!=0.
                # expression = [float(item) for item in view]
                mean = float(np.nanmean(viewnp))
                stdev = float(np.nanstd(viewnp))
                result[gene] = {"truncatedExpression": {}, "rawExpression": {}}
                result[gene]["rawExpression"] = {
                    "mean": mean,
                    "stdev": stdev,
                    "expression": view,
                }

                viewTr = truncatedR[gene]
                viewnpTr = np.array(viewTr, dtype=np.float)
                minimum = float(np.nanmin(viewnpTr))
                maximum = float(np.nanmax(viewnpTr))
                result[gene]["truncatedExpression"] = {
                                    "min": minimum,
                                    "max": maximum,
                                    "expression": viewTr,
                                }              
        return self._format_result(result)

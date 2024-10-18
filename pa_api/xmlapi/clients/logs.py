from typing import List, Optional, Tuple

from pa_api.xmlapi import types
from pa_api.xmlapi.clients.base import ClientProxy
from pa_api.xmlapi.utils import (
    wait,
)


class Log(ClientProxy):
    # def _post_init(self):
    #     ...

    def _request_log(
        self,
        log_type: str,
        query: Optional[str] = None,
        skip: Optional[int] = None,
        nlogs: Optional[int] = None,
        vsys=None,
        params=None,
        remove_blank_text=True,
        timeout=None,
    ) -> str:
        if params is None:
            params = {}
        if query is not None:
            params["query"] = query
        if skip is not None:
            params["skip"] = skip
        if nlogs is not None:
            params["nlogs"] = nlogs
        params = {"log-type": log_type, **params}
        res = self._base_request(
            "log",
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            timeout=timeout,
        )
        job_id = res.xpath(".//job/text()")[0]
        return job_id

    # https://knowledgebase.paloaltonetworks.com/KCSArticleDetail?id=kA14u000000g1YbCAI#:~:text=%3Cline%3Equery%20job%20enqueued%20with%20jobid%2023%3C%2Fline%3E%20%3E%3E%3E%3E%20Note,off.%20In%20this%20example%20the%20jobid%20%3D%2023
    def get_logs(
        self,
        jobid: str,
        vsys=None,
        params=None,
        remove_blank_text=True,
        timeout=None,
    ) -> Tuple[types.LogJob, List[types.Log]]:
        if params is None:
            params = {}
        params = {"action": "get", "job-id": jobid}
        res = self._base_request(
            "log",
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            timeout=timeout,
        )
        job_xml = res.xpath(".//job")[0]
        logs_xml = res.xpath(".//log/logs/entry")
        return types.LogJob.from_xml(job_xml), [types.Log.from_xml(e) for e in logs_xml]

    def _wait_job_completion(
        self, job_id: str, waiter=None
    ) -> Tuple[types.LogJob, List[types.Log]]:
        """
        Block until the job complete.

        job_id: the job to wait upon
        waiter: a generator that yield when a new query must be done.
                see `wait` function (the default waiter) for an example
        """
        if not waiter:
            waiter = wait(pool_delay=5)
        for _ in waiter:
            job, logs = self.get_logs(job_id)
            if job.status == "FIN":
                return job, logs
        raise Exception("Timeout while waiting for job completion")

    def _traffic(
        self,
        query: Optional[str] = None,
        skip: Optional[int] = None,
        nlogs: Optional[int] = None,
        vsys=None,
        timeout=None,
    ) -> str:
        return self._request_log(
            "traffic",
            query=query,
            skip=skip,
            nlogs=nlogs,
            vsys=vsys,
            timeout=timeout,
        )

    def get_traffic_logs(
        self,
        query: Optional[str] = None,
        skip: Optional[int] = None,
        nlogs: Optional[int] = None,
        vsys=None,
        timeout=None,
    ) -> List[types.Log]:
        jobid = self._traffic(
            query=query,
            skip=skip,
            nlogs=nlogs,
            vsys=vsys,
            timeout=timeout,
        )
        _job, logs = self._wait_job_completion(jobid)
        return logs

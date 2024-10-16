from typing import List, Union

from pa_api.xmlapi import types
from pa_api.xmlapi.clients.operations.base import OperationProxy
from pa_api.xmlapi.utils import (
    Element,
    wait,
)


class Job(OperationProxy):
    def _raw_get_jobs(self, job_ids: Union[None, str, List[str]] = None) -> Element:
        """
        Get information of job(s) as an XML object.
        Retrieve all jobs by default.

        If job_id is provided, then only retrieve the job requested.
        """
        filter = "<all></all>"
        if job_ids:
            if isinstance(job_ids, str):
                job_ids = [job_ids]
            filter = "".join(f"<id>{j}</id>" for j in job_ids)
        cmd = f"<show><jobs>{filter}</jobs></show>"
        return self._request(cmd)

    def get_jobs(self, job_ids: Union[None, str, List[str]] = None) -> List[types.Job]:
        """
        Get information of job(s)
        Retrieve all jobs by default.

        If job_id is provided, then only retrieve the job requested.
        """
        job_xmls = self._raw_get_jobs(job_ids).xpath(".//job")
        transformed = (types.Job.from_xml(x) for x in job_xmls)
        return [j for j in transformed if j]

    def get_job(self, job_id) -> types.Job:
        """
        Get information of job(s)
        Retrieve all jobs by default.

        If job_id is provided, then only retrieve the job requested.
        """
        return self.get_jobs(job_id)[0]

    def wait_job_completion(self, job_id: str, waiter=None) -> types.Job:
        """
        Block until the job complete.

        job_id: the job to wait upon
        waiter: a generator that yield when a new query must be done.
                see `wait` function (the default waiter) for an example
        """
        if not waiter:
            waiter = wait()
        for _ in waiter:
            job = self.get_job(job_id)
            if job.progress >= 100:
                return job
            self.logger.info(f"Job {job_id} progress: {job.progress}")
        raise Exception("Timeout while waiting for job completion")

    def raw_get_pending_jobs(self):
        """
        Get all the jobs that are pending as a XML object
        """
        cmd = "<show><jobs><pending></pending></jobs></show>"
        return self._request(cmd)

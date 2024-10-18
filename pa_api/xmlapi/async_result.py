from typing import TYPE_CHECKING

from pa_api.xmlapi.types import Job

if TYPE_CHECKING:
    from .clients import Client


class AsyncResult:
    def __init__(self, client: "Client", job_id: str) -> None:
        self._client = client
        self._job_id = job_id

    @property
    def job_id(self):
        return self._job_id

    def get_state(self) -> Job:
        return self._client.operation.job.get_job(self.job_id)

    def fetch(self) -> Job:
        return self._client.operation.job.get_job(self.job_id)

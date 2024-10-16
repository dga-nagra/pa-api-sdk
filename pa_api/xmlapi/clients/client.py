from pa_api.xmlapi.utils import (
    Element,
    el2dict,
)

from .base import BaseXMLApiClient
from .commit import Commit
from .config import Config
from .logs import Log
from .misc import Misc
from .operations import Operation


class Client(BaseXMLApiClient):
    operation: Operation
    configuration: Config
    commit: Commit
    logs: Log
    misc: Misc

    def _post_init(self):
        self.configuration = Config(self)
        self.operation = Operation(self)
        self.commit = Commit(self)
        self.logs = Log(self)
        self.misc = Misc(self)

    # https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api/pan-os-xml-api-request-types/export-files-api
    # https://knowledgebase.paloaltonetworks.com/KCSArticleDetail?id=kA10g000000ClaOCAS#:~:text=From%20the%20GUI%2C%20go%20to%20Device%20%3E%20Setup,%3E%20scp%20export%20configuration%20%5Btab%20for%20command%20help%5D
    def _export_request(
        self,
        category,
        method="GET",
        params=None,
        verify=None,
        stream=None,
        timeout=None,
    ):
        if params is None:
            params = {}
        params = {"category": category, **params}
        return self._request(
            "export",
            method=method,
            params=params,
            verify=verify,
            parse=False,
            stream=stream,
            timeout=timeout,
        ).content

    def export_configuration(
        self,
        verify=None,
        timeout=None,
    ) -> Element:
        return self._export_request(
            category="configuration",
            verify=verify,
            timeout=timeout,
        )

    def export_device_state(
        self,
        verify=None,
        timeout=None,
    ) -> Element:
        return self._export_request(
            category="device-state",
            verify=verify,
            timeout=timeout,
        )

    # https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api/pan-os-xml-api-request-types/get-version-info-api
    def api_version(self):
        return el2dict(
            self._request(
                "version",
                method="POST",
            ).xpath(".//result")[0]
        )["result"]

    def _check_is_panorama(self) -> bool:
        return self.configuration.check_is_panorama()

    @property
    def ispanorama(self):
        if self._ispanorama is None:
            self._ispanorama = self._check_is_panorama()
        return self._ispanorama

from typing import Optional

from pa_api.xmlapi.clients.base import ClientProxy
from pa_api.xmlapi.utils import (
    Element,
)


class Log(ClientProxy):
    # def _post_init(self):
    #     ...

    def _request(
        self,
        log_type: str,
        skip: Optional[int] = None,
        nlogs: Optional[int] = None,
        vsys=None,
        params=None,
        remove_blank_text=True,
        timeout=None,
    ) -> Element:
        if params is None:
            params = {}
        if skip is not None:
            params["skip"] = skip
        if nlogs is not None:
            params["nlogs"] = nlogs
        params = {"log-type": log_type, **params}
        return self._base_request(
            "log",
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            timeout=timeout,
        )

    def _traffic(
        self,
        skip: Optional[int] = None,
        nlogs: Optional[int] = None,
        vsys=None,
        params=None,
        remove_blank_text=True,
        timeout=None,
    ) -> Element:
        return self._request(
            "traffic",
            skip=skip,
            nlogs=nlogs,
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            timeout=timeout,
        )

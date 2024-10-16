from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .operation import Operation


class OperationProxy:
    def __init__(self, client: "Operation") -> None:
        self._client = client

    @property
    def logger(self):
        return self._client.logger

    def _request(
        self,
        method="GET",
        vsys=None,
        params=None,
        remove_blank_text=True,
        parse=True,
        stream=None,
        timeout=None,
    ):
        return self._client._request(  # noqa: SLF001
            method=method,
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            parse=parse,
            stream=stream,
            timeout=timeout,
        )

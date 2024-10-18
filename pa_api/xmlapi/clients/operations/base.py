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
        cmd,
        method="GET",
        vsys=None,
        params=None,
        remove_blank_text=True,
        timeout=None,
    ):
        return self._client._request(  # noqa: SLF001
            cmd,
            method=method,
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            timeout=timeout,
        )

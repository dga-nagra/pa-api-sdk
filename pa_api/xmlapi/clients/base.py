import abc
import logging
from typing import TYPE_CHECKING, Optional

from pa_api.utils import clean_url_host, get_credentials_from_env
from pa_api.xmlapi.base import raw_request
from pa_api.xmlapi.utils import (
    el2dict,
)

if TYPE_CHECKING:
    from .client import Client


class BaseXMLApiClient:
    def __init__(
        self,
        host=None,
        api_key=None,
        ispanorama=None,
        verify=False,
        timeout=None,
        logger=None,
    ):
        env_host, env_apikey = get_credentials_from_env()
        host = host or env_host
        api_key = api_key or env_apikey
        if not host:
            raise Exception("Missing Host")
        if not api_key:
            raise Exception("Missing API Key")
        host, _, _ = clean_url_host(host)

        self._host = host
        self._api_key = api_key
        self._url = f"{host}/api"
        self._verify = verify
        self._timeout = timeout
        self._ispanorama = ispanorama
        self.logger = logger or logging

        self._post_init()

    def _post_init(self): ...

    def _base_request(
        self,
        type,
        method="GET",
        vsys=None,
        params=None,
        remove_blank_text=True,
        parse=True,
        stream=None,
        timeout=None,
    ):
        if timeout is None:
            timeout = self._timeout
        headers = {"X-PAN-KEY": self._api_key}
        return raw_request(
            self._url,
            type,
            method,
            vsys=vsys,
            params=params,
            headers=headers,
            remove_blank_text=remove_blank_text,
            verify=self._verify,
            logger=self.logger,
            parse=parse,
            stream=stream,
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

    # https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api/get-started-with-the-pan-os-xml-api/get-your-api-key
    @staticmethod
    def generate_apikey(
        username: str,
        password: str,
        host: Optional[str] = None,
        verify=False,
        timeout=None,
    ) -> str:
        """
        Generate a new API-Key for the user connected.
        """
        env_host, _ = get_credentials_from_env()
        host = host or env_host
        if not host:
            raise Exception("Missing Host")
        base_url, _, _ = clean_url_host(host)
        params = {"user": username, "password": password}
        return raw_request(
            f"{base_url}/api",
            type="keygen",
            method="POST",
            params=params,
            verify=verify,
            timeout=timeout,
        ).xpath(".//key/text()")[0]


class ClientProxy(abc.ABC):
    def __init__(self, client: "Client") -> None:
        self._client = client
        self._post_init()

    def _post_init(self): ...

    @property
    def logger(self) -> logging.Logger:
        return self._client.logger

    def _base_request(
        self,
        type,
        method="GET",
        vsys=None,
        params=None,
        remove_blank_text=True,
        parse=True,
        stream=None,
        timeout=None,
    ):
        return self._client._base_request(  # noqa: SLF001
            type,
            method=method,
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            parse=parse,
            stream=stream,
            timeout=timeout,
        )

    # @abc.abstractmethod
    # def _request(
    #     self,
    #     cmd,
    #     method="POST",
    #     vsys=None,
    #     params=None,
    #     remove_blank_text=True,
    #     timeout=None,
    # ) -> Element:
    #     pass

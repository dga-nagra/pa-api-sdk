from typing import List, Optional

from pa_api.utils import first
from pa_api.xmlapi import types
from pa_api.xmlapi.clients.base import ClientProxy
from pa_api.xmlapi.utils import (
    Element,
)


class Config(ClientProxy):
    def _request(
        self,
        xpath,
        action="get",
        method="GET",
        vsys=None,
        params=None,
        remove_blank_text=True,
        timeout=None,
    ) -> Element:
        if params is None:
            params = {}
        params = {"action": action, "xpath": xpath, **params}
        return self._base_request(
            "config",
            method=method,
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            timeout=timeout,
        )

    def get(self, xpath: str):
        """
        This will retrieve the xml definition based on the xpath
        The xpath doesn't need to be exact
        and can select multiple values at once.
        Still, it must at least speciy /config at is begining
        """
        return self._request(xpath, action="show", method="GET")

    def delete(self, xpath: str):
        """
        This will REMOVE the xml definition at the provided xpath.
        The xpath must be exact.
        """
        return self._request(
            xpath,
            action="delete",
            method="DELETE",
        )

    def create(self, xpath: str, xml_definition):
        """
        This will ADD the xml definition
        INSIDE the element at the provided xpath.
        The xpath must be exact.
        """
        # https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api/pan-os-xml-api-request-types/configuration-api/set-configuration
        params = {"element": xml_definition}
        return self._request(
            xpath,
            action="set",
            method="POST",
            params=params,
        )

    def update(self, xpath: str, xml_definition):
        """
        This will REPLACE the xml definition
        INSTEAD of the element at the provided xpath
        The xpath must be exact.
        Nb: We can pull the whole config, update it locally,
        and push the final result
        """
        # https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api/pan-os-xml-api-request-types/configuration-api/set-configuration
        params = {"element": xml_definition}
        return self._request(
            xpath,
            action="edit",
            method="POST",
            params=params,
        )

    def check_is_panorama(self) -> bool:
        try:
            self._request("/config/panorama/vsys")
            return False
        except Exception:
            return True

    def raw_get_local_panorama(self):
        return self._request(
            "/config/devices/entry/deviceconfig/system/panorama/local-panorama/panorama-server"
        )

    def get_local_panorama_ip(self) -> Optional[str]:
        res = self.raw_get_local_panorama()
        return first(res.xpath("//panorama-server/text()"))

    def _raw_get_addresses(self):
        """
        Return the list of addresses known from Panorama as a XML object.
        NOTE: This only works if the client is a Firewall.
        """
        if self._client.ispanorama:
            return self._request("/config/devices/entry/device-group/entry/address")
        return self._request("/config/panorama/vsys//address")

    def get_addresses(self) -> List[types.Address]:
        """
        Return the list of addresses known from Panorama as a python structure.
        NOTE: This only works if the client is a Firewall.
        """
        res = self._raw_get_addresses()
        addresses = res.xpath(".//address/entry")
        return [types.Address.from_xml(i) for i in addresses]

    def _raw_get_routing_tables(self) -> Element:
        """
        Return the list of interfaces known from Panorama as a XML object.
        NOTE: This only works if the client is a Firewall.
        """
        return self._request(
            "/config/devices/entry/network/virtual-router/entry/routing-table"
        )

    def get_routing_tables(self) -> List[types.RoutingTable]:
        """
        Return the list of interface known from Panorama as a python structure.
        NOTE: This only works if the client is a Firewall.
        """
        res = self._raw_get_routing_tables()
        routing_tables = res.xpath(".//routing-table")
        # print(len(routing_tables))
        # from pa_api.xmlapi.utils import pprint
        # for r in routing_tables:
        #     pprint(r)
        return [types.RoutingTable.from_xml(i) for i in routing_tables]

    def _raw_get_interfaces(self) -> Element:
        """
        Return the list of interfaces known from Panorama as a XML object.
        NOTE: This only works if the client is a Firewall.
        """
        return self._request("/config/devices/entry/network/interface")

    def get_interfaces(self) -> List[types.Interface]:
        """
        Return the list of interface known from Panorama as a python structure.
        NOTE: This only works if the client is a Firewall.
        """
        res = self._raw_get_interfaces()
        interfaces = res.xpath(".//interface")
        return [types.Interface.from_xml(i) for i in interfaces]

    def _raw_get_zones(self) -> Element:
        """
        Return the list of zones known from Panorama as a XML object.
        NOTE: This only works if the client is a Firewall.
        """
        if self._client.ispanorama:
            return self._request(
                "/config/devices/entry/*/entry/config/devices/entry/vsys/entry/zone"
            )
        return self._request("/config/devices/entry/vsys/entry/zone")

    def get_zones(self) -> Element:
        """
        Return the list of zones known from Panorama as a python structure.
        NOTE: This only works if the client is a Firewall.
        """
        res = self._raw_get_zones()
        zones = res.xpath(".//zone/entry")
        return [types.Zone.from_xml(i) for i in zones]

from typing import List, Optional, Tuple

from pa_api.xmlapi import types
from pa_api.xmlapi.clients.operations.base import OperationProxy
from pa_api.xmlapi.utils import (
    Element,
)


class HA(OperationProxy):
    def set_ha_status(self, active: bool = True, target: Optional[str] = None):
        """
        Activate or Deactivate (suspend) the HA pair.

        """
        status = "<functional></functional>" if active else "<suspend></suspend>"
        cmd = f"<request><high-availability><state>{status}</state></high-availability></request>"
        params = {"target": target} if target else None
        return self._request(cmd, params=params).xpath(".//result/text()")[0]

    def set_ha_preemption(self, active=True, target=None):
        """
        NOT WORKING:
        There is currently no way to deactivate the preemption using the API.
        """
        raise Exception("set_ha_preemption not implementend")

    def _raw_get_ha_info(self, state_only=False, target=None) -> Element:
        """
        Get the current state of a HA pair as a XML object.
        """
        filter = "<state></state>" if state_only else "<all></all>"
        cmd = f"<show><high-availability>{filter}</high-availability></show>"
        params = {"target": target} if target else None
        return self._request(cmd, params=params)

    def get_ha_info(self, state_only=False, target=None) -> types.HAInfo:
        """
        Get the current state of a HA pair as a python object.
        """
        res = self._raw_get_ha_info(state_only=state_only, target=target)
        hainfo_xml = res.xpath(".//result")[0]
        # pprint(hainfo_xml)
        return types.HAInfo.from_xml(hainfo_xml)

    def get_ha_pairs(
        self, connected=True
    ) -> Tuple[List[Tuple[types.Device, Optional[types.Device]]], List[types.Device]]:
        """
        Retrieve a tuple containing 2 values:
        1. The list of HA pairs and their members
        2. A list of devices that are not part of a HA pair
        """
        # Get all devices and index them using their serial number
        devices: List[types.Device] = self._client.get_devices(connected=connected)
        device_map = {d.serial: d for d in devices}

        # Create the 2 lists by iterating over the devices
        done = set()
        ha_pairs = []
        without_ha = []
        for d in devices:
            # Do not manage twice the same device
            if d.serial in done:
                continue
            # The device does not have an HA peer
            if not d.ha_peer_serial:
                without_ha.append(d)
                done.add(d.serial)
                continue
            # Get the current device's HA peer
            # push them in the ha_pairs list
            # and mark both of them as done
            peer = device_map.get(d.ha_peer_serial)
            ha_pairs.append((d, peer))
            done.update((d.serial, d.ha_peer_serial))
        return ha_pairs, without_ha

    def get_ha_pairs_map(self, connected=True):
        """
        Same as `get_ha_pairs`, but the ha_pairs are return as a map.
        This provides an easier and more readable lookup to find a pair:

        mapping, _ = client.get_ha_pairs_map()
        serial = "12345"
        pair_of_serial = mapping[serial]
        """
        ha_pairs, without_ha = self.get_ha_pairs(connected=connected)
        map = {}
        for pair in ha_pairs:
            for device in pair:
                map[device.serial] = pair
        return map, without_ha

from typing import List, Optional, Union

from pa_api.xmlapi import types
from pa_api.xmlapi.clients.base import ClientProxy
from pa_api.xmlapi.utils import (
    Element,
)

from .config import Config
from .ha import HA
from .job import Job
from .lock import Lock


class Operation(ClientProxy):
    def _post_init(self):
        self.lock = Lock(self)
        self.config = Config(self)
        self.ha = HA(self)
        self.job = Job(self)

    def _request(
        self,
        cmd,
        method="POST",
        vsys=None,
        params=None,
        remove_blank_text=True,
        timeout=None,
    ) -> Element:
        if params is None:
            params = {}
        params = {"cmd": cmd, **params}
        return self._base_request(
            "op",
            method=method,
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            timeout=timeout,
        )

    def __call__(
        self,
        cmd,
        method="POST",
        params=None,
        remove_blank_text=True,
    ):
        return self._request(
            cmd,
            method=method,
            params=params,
            remove_blank_text=remove_blank_text,
        )

    def _raw_get_versions(self) -> Element:
        """
        Get the versions informations as a XML object.
        """
        cmd = "<request><system><software><check></check></software></system></request>"
        return self._request(cmd)

    def get_versions(self) -> List[types.SoftwareVersion]:
        """
        Get the versions informations
        """
        res = self._raw_get_versions()
        return [
            types.SoftwareVersion.from_xml(entry)
            for entry in res.xpath(".//sw-updates/versions/entry")
        ]

    def get_panorama_status(self):
        """
        Get the current status of Panorama server.
        """
        cmd = "<show><panorama-status></panorama-status></show>"
        return self._request(cmd).xpath(".//result")

    def _raw_get_devices(self, connected=False):
        """
        Return the list of device known from Panorama as a XML object.
        NOTE: This only works if the client is a Panorama server.

        connected: only returns the devices that are connected
        """
        # This only works on Panorama, not the FW
        filter = "<connected></connected>" if connected else "<all></all>"
        cmd = f"<show><devices>{filter}</devices></show>"
        return self._request(cmd)

    def get_devices(self, connected=False) -> List[types.Device]:
        """
        Return the list of device known from Panorama as a python structure.
        NOTE: This only works if the client is a Panorama server.

        connected: only returns the devices that are connected
        """
        res = self._raw_get_devices(connected=connected)
        entries = res.xpath(".//devices/entry")
        devices = (types.Device.from_xml(e) for e in entries)
        return [d for d in devices if d]

    def _raw_get_dg_hierarchy(self):
        """
        Return the hierarchy of device groups as a XML object.
        """
        cmd = "<show><dg-hierarchy></dg-hierarchy></show>"
        return self._request(cmd)

    def get_plan_dg_hierarchy(self, recursive=False):
        """
        Return the hierarchy of device groups as a dict.
        The keys are the names of the device groups.

        The values are the children device groups and depends on the recursive parameter.
        recursive: if False, the values are only the direct children of the device group.
            Otherwise, the values are all the descendant device groups.
        """
        devicegroups = {}  # name: children
        hierarchy = self._raw_get_dg_hierarchy().xpath(".//dg-hierarchy")[0]
        xpath = ".//dg" if recursive else "./dg"
        for dg in hierarchy.xpath(".//dg"):
            devicegroups[dg.attrib["name"]] = [
                x.attrib["name"] for x in dg.xpath(xpath)
            ]
        return devicegroups

    def _raw_get_templates(self, name=None) -> Element:
        """
        Return the synchronization status the templates per devices as a XML object.
        A device is in sync if it is up-to-date with the current version on Panorama.
        NOTE: This only works on Panorama.
        """
        # This only works on Panorama, not the FW
        filter = f"<name>{name}</name>" if name else ""
        cmd = f"<show><templates>{filter}</templates></show>"
        return self._request(cmd)

    def get_templates_sync_status(self):
        """
        Return the synchronization status the templates per devices
        A device is in sync if it is up-to-date with the current version on Panorama.
        NOTE: This only works on Panorama.

        The result is a list of tuple of 3 values:
        1. the template's name
        2. the device's name
        3. the sync status
        """
        res = self._raw_get_templates()
        statuses = []
        for entry in res.xpath("./result/templates/entry"):
            template_name = entry.attrib["name"]
            for device in entry.xpath("./devices/entry"):
                device_name = device.attrib["name"]
                template_status = next(device.xpath("./template-status/text()"), None)
                status = (template_name, device_name, template_status)
                statuses.append(status)
        return statuses

    def _raw_get_vpn_flows(self, name=None) -> List[Element]:
        """
        Returns the VPN flow information as a XML object.
        NOTE: This only works on Panorama server, not firewalls
        """
        # This only works on Panorama, not the FW"
        filter = f"<name>{name}</name>" if name else "<all></all>"
        cmd = f"<show><vpn><flow>{filter}</flow></vpn></show>"
        return self._request(cmd)

    def get_vpn_flows(self, name=None):
        """
        Returns the VPN flow information as a python structure.
        NOTE: This only works on Panorama server, not firewalls
        """
        entries = self._raw_get_vpn_flows(name=name).xpath(".//IPSec/entry")
        return [types.VPNFlow.from_xml(e) for e in entries]

    def _raw_system_info(self):
        """
        Returns informations about the system as a XML object.
        """
        cmd = "<show><system><info></info></system></show>"
        return self._request(cmd)

    def system_info(self) -> types.operations.SystemInfo:
        """
        Returns informations about the system as a XML object.
        """
        xml = self._raw_system_info()
        info = xml.xpath("./result/system")[0]
        return types.operations.SystemInfo.from_xml(info)

    def _raw_system_resources(self):
        """
        Get the system resouces as a XML object.
        NOTE: The string is the raw output of a `ps` command.
        """
        cmd = "<show><system><resources></resources></system></show>"
        return self._request(cmd)

    def system_resources(self):
        """
        Get the system resouces as a string.
        The string is the raw output of a `ps` command.
        """
        res = self._raw_system_resources()
        text = res.xpath(".//result/text()")[0]
        return text.split("\n\n")[0]

    def _raw_download_software(self, version):
        """
        Download the software version on the device.
        version: the software version to download
        """
        cmd = f"<request><system><software><download><version>{version}</version></download></software></system></request>"
        return self._request(cmd)

    def download_software(self, version) -> Optional[str]:
        """
        Download the software version on the device.
        version: the software version to download

        Returns the download job's ID in case of successful launch,
        None is returned otherwise.
        """
        res = self._raw_download_software(version)
        try:
            return res.xpath(".//job/text()")[0]
        except Exception:
            self.logger.debug("Download has not started")
        return None

    def _raw_install_software(self, version):
        """
        Install the software version on the device.
        version: the software version to install
        """
        cmd = f"<request><system><software><install><version>{version}</version></install></software></system></request>"
        return self._request(cmd)

    def install_software(
        self, version: Union[None, str, types.SoftwareVersion]
    ) -> Optional[str]:
        """
        Install the software version on the device.
        version: the software version to install

        Returns the download job's ID in case of successful launch,
        None is returned otherwise.
        """
        if isinstance(version, types.SoftwareVersion):
            version = version.version
        res = self._raw_install_software(version)
        try:
            return res.xpath(".//job/text()")[0]
        except Exception:
            self.logger.debug("Download has not started")
        return None

    def _raw_restart(self):
        """
        Restart the device
        """
        cmd = "<request><restart><system></system></restart></request>"
        return self._request(cmd)

    def restart(self):
        """
        Restart the device
        """
        return "".join(self._raw_restart().xpath(".//result/text()"))

    # def _get_rule_use(self, device_group, position, rule_type, number: int = 200):
    #     results = []
    #     for i in range(100):
    #         cmd = _get_rule_use_cmd(
    #             device_group,
    #             position,
    #             rule_type,
    #             i * number,
    #             number,
    #         )
    #         res = self._request(cmd).xpath("result")[0]
    #         total_count = int(res.attrib["total-count"])
    #         results.extend(res.xpath("entry"))
    #         if len(results) >= total_count:
    #             break
    #     return results

    # def get_rule_use(self, tree=None, max_threads: Optional[int] = None):
    #     if tree is None:
    #         tree = self.get_tree()
    #     device_groups = tree.xpath("devices/*/device-group/*/@name")
    #     positions = ("pre", "post")
    #     # rule_types = tuple({x.tag for x in tree.xpath(
    #     # "devices/*/device-group/*"
    #     # "/*[self::post-rulebase or self::pre-rulebase]/*")})
    #     rule_types = ("security", "pbf", "nat", "application-override")
    #     args_list = list(product(device_groups, positions, rule_types))

    #     def func(args):
    #         return self._get_rule_use(*args)

    #     threads = len(args_list)
    #     threads = min(max_threads or threads, threads)
    #     with Pool(len(args_list)) as pool:
    #         data = pool.map(func, args_list)
    #     return [entry for entry_list in data for entry in entry_list]

    # def _get_rule_hit_count(self, device_group, rulebase, rule_type):
    #     cmd = (
    #         "<show><rule-hit-count><device-group>"
    #         f"<entry name='{device_group}'><{rulebase}><entry name='{rule_type}'>"
    #         f"<rules><all/></rules></entry></{rulebase}></entry>"
    #         "</device-group></rule-hit-count></show>"
    #     )
    #     res = self._request(cmd)
    #     entries = res.xpath(".//rules/entry") or []
    #     # return entries
    #     return [(device_group, rulebase, rule_type, e) for e in entries]

    # def get_rule_hit_count(self, tree=None, max_threads=None):
    #     if tree is None:
    #         tree = self.get_tree()
    #     device_groups = tree.xpath("devices/*/device-group/*/@name")
    #     rulebases = ("pre-rulebase", "post-rulebase")
    #     rule_types = ("security", "pbf", "nat", "application-override")
    #     args_list = list(product(device_groups, rulebases, rule_types))

    #     def func(args):
    #         return self._get_rule_hit_count(*args)

    #     threads = len(args_list)
    #     threads = min(max_threads or threads, threads)
    #     with Pool(len(args_list)) as pool:
    #         data = pool.map(func, args_list)
    #     return [entry for entry_list in data for entry in entry_list]

    # def _extend_tree_information(
    #     self,
    #     tree,
    #     extended=None,
    #     max_threads=None,
    # ):
    #     """
    #     Incorporate usage statistics into the configuration.
    #     tree: the configuration as a XML object
    #     extended: rule-use data (if not provided, the function will retrieve them automatically)
    #     """
    #     if extended is None:
    #         extended = self.get_rule_use(tree, max_threads=max_threads)
    #     rules = tree.xpath(
    #         ".//device-group/entry/"
    #         "*[self::pre-rulebase or self::post-rulebase]/*/rules/entry[@uuid]",
    #     )
    #     ext_dict = {x.attrib.get("uuid"): x for x in extended}
    #     rules_dict = {x.attrib["uuid"]: x for x in rules}
    #     for ext, rule in map_dicts(ext_dict, rules_dict):
    #         extend_element(rule, ext)
    #         # NOTE: Do not use rule.extend(ext)
    #         # => This is causing duplicates entries
    #     return tree, extended

    # def get_tree(self, extended=False) -> Element:
    #     """
    #     Return the running configuration
    #     The differences with `running_config` are not known
    #     """
    #     tree = get_tree(
    #         self._host, self._api_key, verify=self._verify, logger=self.logger
    #     )
    #     if extended:
    #         self._extend_tree_information(tree)
    #     return tree

    # def _extend_tree_information(
    #     self,
    #     tree,
    #     extended=None,
    #     max_threads=None,
    # ):
    #     """
    #     Incorporate usage statistics into the configuration.
    #     tree: the configuration as a XML object
    #     extended: rule-use data (if not provided, the function will retrieve them automatically)
    #     """
    #     if extended is None:
    #         extended = self.get_rule_use(tree, max_threads=max_threads)
    #     rules = tree.xpath(
    #         ".//device-group/entry/"
    #         "*[self::pre-rulebase or self::post-rulebase]/*/rules/entry[@uuid]",
    #     )
    #     ext_dict = {x.attrib.get("uuid"): x for x in extended}
    #     rules_dict = {x.attrib["uuid"]: x for x in rules}
    #     for ext, rule in map_dicts(ext_dict, rules_dict):
    #         extend_element(rule, ext)
    #         # NOTE: Do not use rule.extend(ext)
    #         # => This is causing duplicates entries
    #     return tree, extended

import logging
from itertools import chain, product
from multiprocessing.pool import ThreadPool as Pool
from typing import List, Optional, Tuple, Union

from pa_api.utils import clean_url_host, first, get_credentials_from_env
from pa_api.xmlapi.base import _get_rule_use_cmd, get_tree, raw_request
from pa_api.xmlapi.exceptions import ServerError
from pa_api.xmlapi.utils import (
    Element,
    el2dict,
    extend_element,
    map_dicts,
    wait,
)

from . import types


class XMLApi:
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

    def _request(
        self,
        type,
        method="GET",
        vsys=None,
        params=None,
        remove_blank_text=True,
        verify=None,
        parse=True,
        stream=None,
        timeout=None,
    ):
        if verify is None:
            verify = self._verify
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
            verify=verify,
            logger=self.logger,
            parse=parse,
            stream=stream,
            timeout=timeout,
        )

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

    def _conf_request(
        self,
        xpath,
        action="get",
        method="GET",
        vsys=None,
        params=None,
        remove_blank_text=True,
        verify=None,
        timeout=None,
    ) -> Element:
        if params is None:
            params = {}
        params = {"action": action, "xpath": xpath, **params}
        return self._request(
            "config",
            method=method,
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            verify=verify,
            timeout=timeout,
        )

    def _op_request(
        self,
        cmd,
        method="POST",
        vsys=None,
        params=None,
        remove_blank_text=True,
        verify=None,
        timeout=None,
    ) -> Element:
        if params is None:
            params = {}
        params = {"cmd": cmd, **params}
        return self._request(
            "op",
            method=method,
            vsys=vsys,
            params=params,
            remove_blank_text=remove_blank_text,
            verify=verify,
            timeout=timeout,
        )

    def _commit_request(
        self,
        cmd,
        method="POST",
        params=None,
        remove_blank_text=True,
        verify=None,
        timeout=None,
    ):
        if params is None:
            params = {}
        params = {"cmd": cmd, **params}
        return self._request(
            "commit",
            method=method,
            params=params,
            remove_blank_text=remove_blank_text,
            verify=verify,
            timeout=timeout,
        )

    # https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api/get-started-with-the-pan-os-xml-api/get-your-api-key
    def generate_apikey(self, username, password: str) -> str:
        """
        Generate a new API-Key for the user connected.
        """
        params = {"user": username, "password": password}
        return self._request(
            "keygen",
            method="POST",
            params=params,
        ).xpath(".//key/text()")[0]

    # https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api/pan-os-xml-api-request-types/get-version-info-api
    def api_version(self):
        return el2dict(
            self._request(
                "version",
                method="POST",
            ).xpath(".//result")[0]
        )["result"]

    def configuration(
        self,
        xpath,
        action="get",
        method="GET",
        params=None,
        remove_blank_text=True,
    ):
        return self._conf_request(
            xpath,
            action=action,
            method=method,
            params=params,
            remove_blank_text=remove_blank_text,
        )

    def operation(
        self,
        cmd,
        method="POST",
        params=None,
        remove_blank_text=True,
    ):
        return self._op_request(
            cmd,
            method=method,
            params=params,
            remove_blank_text=remove_blank_text,
        )

    def _check_is_panorama(self) -> bool:
        try:
            self.configuration("/config/panorama/vsys")
            return False
        except Exception:
            return True

    @property
    def ispanorama(self):
        if self._ispanorama is None:
            self._ispanorama = self._check_is_panorama()
        return self._ispanorama

    def get_tree(self, extended=False) -> Element:
        """
        Return the running configuration
        The differences with `running_config` are not known
        """
        tree = get_tree(
            self._host, self._api_key, verify=self._verify, logger=self.logger
        )
        if extended:
            self._extend_tree_information(tree)
        return tree

    def _get_rule_use(self, device_group, position, rule_type, number: int = 200):
        results = []
        for i in range(100):
            cmd = _get_rule_use_cmd(
                device_group,
                position,
                rule_type,
                i * number,
                number,
            )
            res = self._op_request(cmd).xpath("result")[0]
            total_count = int(res.attrib["total-count"])
            results.extend(res.xpath("entry"))
            if len(results) >= total_count:
                break
        return results

    def get_rule_use(self, tree=None, max_threads: Optional[int] = None):
        if tree is None:
            tree = self.get_tree()
        device_groups = tree.xpath("devices/*/device-group/*/@name")
        positions = ("pre", "post")
        # rule_types = tuple({x.tag for x in tree.xpath(
        # "devices/*/device-group/*"
        # "/*[self::post-rulebase or self::pre-rulebase]/*")})
        rule_types = ("security", "pbf", "nat", "application-override")
        args_list = list(product(device_groups, positions, rule_types))

        def func(args):
            return self._get_rule_use(*args)

        threads = len(args_list)
        threads = min(max_threads or threads, threads)
        with Pool(len(args_list)) as pool:
            data = pool.map(func, args_list)
        return [entry for entry_list in data for entry in entry_list]

    def _get_rule_hit_count(self, device_group, rulebase, rule_type):
        cmd = (
            "<show><rule-hit-count><device-group>"
            f"<entry name='{device_group}'><{rulebase}><entry name='{rule_type}'>"
            f"<rules><all/></rules></entry></{rulebase}></entry>"
            "</device-group></rule-hit-count></show>"
        )
        res = self._op_request(cmd)
        entries = res.xpath(".//rules/entry") or []
        # return entries
        return [(device_group, rulebase, rule_type, e) for e in entries]

    def get_rule_hit_count(self, tree=None, max_threads=None):
        if tree is None:
            tree = self.get_tree()
        device_groups = tree.xpath("devices/*/device-group/*/@name")
        rulebases = ("pre-rulebase", "post-rulebase")
        rule_types = ("security", "pbf", "nat", "application-override")
        args_list = list(product(device_groups, rulebases, rule_types))

        def func(args):
            return self._get_rule_hit_count(*args)

        threads = len(args_list)
        threads = min(max_threads or threads, threads)
        with Pool(len(args_list)) as pool:
            data = pool.map(func, args_list)
        return [entry for entry_list in data for entry in entry_list]

    def _extend_tree_information(
        self,
        tree,
        extended=None,
        max_threads=None,
    ):
        """
        Incorporate usage statistics into the configuration.
        tree: the configuration as a XML object
        extended: rule-use data (if not provided, the function will retrieve them automatically)
        """
        if extended is None:
            extended = self.get_rule_use(tree, max_threads=max_threads)
        rules = tree.xpath(
            ".//device-group/entry/"
            "*[self::pre-rulebase or self::post-rulebase]/*/rules/entry[@uuid]",
        )
        ext_dict = {x.attrib.get("uuid"): x for x in extended}
        rules_dict = {x.attrib["uuid"]: x for x in rules}
        for ext, rule in map_dicts(ext_dict, rules_dict):
            extend_element(rule, ext)
            # NOTE: Do not use rule.extend(ext)
            # => This is causing duplicates entries
        return tree, extended

    def get(self, xpath: str):
        """
        This will retrieve the xml definition based on the xpath
        The xpath doesn't need to be exact
        and can select multiple values at once.
        Still, it must at least speciy /config at is begining
        """
        return self._conf_request(xpath, action="show", method="GET")

    def delete(self, xpath: str):
        """
        This will REMOVE the xml definition at the provided xpath.
        The xpath must be exact.
        """
        return self._conf_request(
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
        return self._conf_request(
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
        return self._conf_request(
            xpath,
            action="edit",
            method="POST",
            params=params,
        )

    def revert_changes(self, skip_validated: bool = False):
        """
        Revert all the changes made on Panorama.
        NOTE:
        - This only applies on non-commited changes.
        - This revert everything (not scoped by users)

        skip_validated: Do not revert changes that were validated
        """
        skip = "<skip-validate>yes</skip-validate>" if skip_validated else ""
        cmd = f"<revert><config>{skip}</config></revert>"
        return self._op_request(cmd)

    def validate_changes(self):
        """
        Validated all the changes currently made
        """
        cmd = "<validate><full></full></validate>"
        return self._op_request(cmd)

    def _raw_get_push_scope(self, admin=None):
        """
        Gives detailed information about pending changes
        (e.g. xpath, owner, action, ...)
        """
        filter = f"<admin><member>{admin}</member></admin>" if admin else ""
        cmd = f"<show><config><push-scope>{filter}</push-scope></config></show>"
        return self._op_request(cmd)

    def get_push_scope_devicegroups(self, admin=None):
        """
        Gives detailed information about pending changes
        (e.g. xpath, owner, action, ...)
        """
        scope = self._raw_get_push_scope(admin=admin)
        return list(set(scope.xpath(".//objects/entry[@loc-type='device-group']/@loc")))

    def uncommited_changes(self):
        """
        Gives detailed information about pending changes
        (e.g. xpath, owner, action, ...)
        """
        cmd = "<show><config><list><changes></changes></list></config></show>"
        return self._op_request(cmd)

    def uncommited_changes_summary(self, admin=None):
        """
        Only gives the concern device groups
        """
        admin = (
            f"<partial><admin><member>{admin}</member></admin></partial>"
            if admin
            else ""
        )
        cmd = f"<show><config><list><change-summary>{admin}</change-summary></list></config></show>"
        return self._op_request(cmd)

    def pending_changes(self):
        """
        Result content is either 'yes' or 'no'
        """
        cmd = "<check><pending-changes></pending-changes></check>"
        return self._op_request(cmd)

    def save_config(self, name):
        """
        Create a named snapshot of the current configuration
        """
        cmd = f"<save><config><to>{name}</to></config></save>"
        return "\n".join(self._op_request(cmd).xpath(".//result/text()"))

    def save_device_state(self):
        """
        Create a snapshot of the current device state
        """
        cmd = "<save><device-state></device-state></save>"
        return "\n".join(self._op_request(cmd).xpath(".//result/text()"))

    def get_named_configuration(self, name):
        """
        Get the configuration from a named snapshot as an XML object
        """
        cmd = f"<show><config><saved>{name}</saved></config></show>"
        return self._op_request(cmd, remove_blank_text=False).xpath("./result/config")[
            0
        ]

    def candidate_config(self) -> Element:
        """
        Get the configuration to be commited as an XML object
        """
        cmd = "<show><config><candidate></candidate></config></show>"
        return self._op_request(cmd, remove_blank_text=False)

    def running_config(self) -> Element:
        """
        Get the current running configuration as an XML object
        """
        cmd = "<show><config><running></running></config></show>"
        return self._op_request(cmd, remove_blank_text=False)

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
        return self._op_request(cmd)

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

    def _raw_get_versions(self) -> Element:
        """
        Get the versions informations as a XML object.
        """
        cmd = "<request><system><software><check></check></software></system></request>"
        return self.operation(cmd)

    def get_versions(self) -> List[types.SoftwareVersion]:
        """
        Get the versions informations
        """
        res = self._raw_get_versions()
        return [
            types.SoftwareVersion.from_xml(entry)
            for entry in res.xpath(".//sw-updates/versions/entry")
        ]

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
        return self._op_request(cmd)

    def commit_changes(self, force: bool = False):
        """
        Commit all changes
        """
        cmd = "<commit>{}</commit>".format("<force></force>" if force else "")
        return self._commit_request(cmd)

    def _lock_cmd(self, cmd, vsys, no_exception=False) -> bool:
        """
        Utility function for commands that tries to manipulate the lock
        on Panorama.
        """
        try:
            result = "".join(self._op_request(cmd, vsys=vsys).itertext())
            self.logger.debug(result)
        except Exception as e:
            if no_exception:
                self.logger.error(e)
                return False
            raise
        return True

    # https://github.com/PaloAltoNetworks/pan-os-python/blob/a6b018e3864ff313fed36c3804394e2c92ca87b3/panos/base.py#L4459
    def add_config_lock(self, comment=None, vsys="shared", no_exception=False) -> bool:
        comment = f"<comment>{comment}</comment>" if comment else ""
        cmd = f"<request><config-lock><add>{comment}</add></config-lock></request>"
        return self._lock_cmd(cmd, vsys=vsys, no_exception=no_exception)

    def remove_config_lock(self, vsys="shared", no_exception=False) -> bool:
        cmd = "<request><config-lock><remove></remove></config-lock></request>"
        return self._lock_cmd(cmd, vsys=vsys, no_exception=no_exception)

    def add_commit_lock(self, comment=None, vsys="shared", no_exception=False) -> bool:
        comment = f"<comment>{comment}</comment>" if comment else ""
        cmd = f"<request><commit-lock><add>{comment}</add></commit-lock></request>"
        return self._lock_cmd(cmd, vsys=vsys, no_exception=no_exception)

    def remove_commit_lock(self, vsys="shared", no_exception=False) -> bool:
        cmd = "<request><commit-lock><remove></remove></commit-lock></request>"
        return self._lock_cmd(cmd, vsys=vsys, no_exception=no_exception)

    def set_ha_status(self, active: bool = True, target: Optional[str] = None):
        """
        Activate or Deactivate (suspend) the HA pair.

        """
        status = "<functional></functional>" if active else "<suspend></suspend>"
        cmd = f"<request><high-availability><state>{status}</state></high-availability></request>"
        params = {"target": target} if target else None
        return self._op_request(cmd, params=params).xpath(".//result/text()")[0]

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
        return self._op_request(cmd, params=params)

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
        devices: List[types.Device] = self.get_devices(connected=connected)
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

    def get_panorama_status(self):
        """
        Get the current status of Panorama server.
        """
        cmd = "<show><panorama-status></panorama-status></show>"
        return self.operation(cmd).xpath(".//result")

    def raw_get_local_panorama(self):
        return self.configuration(
            "/config/devices/entry/deviceconfig/system/panorama/local-panorama/panorama-server"
        )

    def get_local_panorama_ip(self) -> Optional[str]:
        res = self.raw_get_local_panorama()
        return first(res.xpath("//panorama-server/text()"))

    def _raw_get_devices(self, connected=False):
        """
        Return the list of device known from Panorama as a XML object.
        NOTE: This only works if the client is a Panorama server.

        connected: only returns the devices that are connected
        """
        # This only works on Panorama, not the FW
        filter = "<connected></connected>" if connected else "<all></all>"
        cmd = f"<show><devices>{filter}</devices></show>"
        return self.operation(cmd)

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
        return self.operation(cmd)

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

    def _raw_get_devicegroups(self):
        """
        Return the list of device groups as a XML object.
        """
        cmd = "<show><devicegroups></devicegroups></show>"
        return self.operation(cmd)

    def get_devicegroups_name(
        self,
        parents=None,
        with_connected_devices=None,
    ):
        """
        This returns the names of the devicegroups:
        - parents: the returned list will only contain children of the provided parents (parents included)
        - with_devices: the returned list will only contain devicegroups that have direct devices under them
        """
        devicegroups = self._raw_get_devicegroups().xpath(".//devicegroups/entry")
        if with_connected_devices:
            names = [
                dg.attrib["name"]
                for dg in devicegroups
                if dg.xpath("./devices/entry/connected[text() = 'yes']")
            ]
        else:
            names = [dg.attrib["name"] for dg in devicegroups]
        if parents:
            hierarchy = self.get_plan_dg_hierarchy(recursive=True)
            tokeep = set(chain(*(hierarchy.get(p, []) for p in parents))) | set(parents)
            names = list(set(names) & tokeep)
        return names

    def _raw_get_addresses(self):
        """
        Return the list of addresses known from Panorama as a XML object.
        NOTE: This only works if the client is a Firewall.
        """
        if self.ispanorama:
            return self.configuration(
                "/config/devices/entry/device-group/entry/address"
            )
        return self.configuration("/config/panorama/vsys//address")

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
        return self.configuration(
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
        return self.configuration("/config/devices/entry/network/interface")

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
        if self.ispanorama:
            return self.configuration(
                "/config/devices/entry/*/entry/config/devices/entry/vsys/entry/zone"
            )
        return self.configuration("/config/devices/entry/vsys/entry/zone")

    def get_zones(self) -> Element:
        """
        Return the list of zones known from Panorama as a python structure.
        NOTE: This only works if the client is a Firewall.
        """
        res = self._raw_get_zones()
        zones = res.xpath(".//zone/entry")
        return [types.Zone.from_xml(i) for i in zones]

    def _raw_get_templates(self, name=None) -> Element:
        """
        Return the synchronization status the templates per devices as a XML object.
        A device is in sync if it is up-to-date with the current version on Panorama.
        NOTE: This only works on Panorama.
        """
        # This only works on Panorama, not the FW
        filter = f"<name>{name}</name>" if name else ""
        cmd = f"<show><templates>{filter}</templates></show>"
        return self.operation(cmd)

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
        return self.operation(cmd)

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
        return self.operation(cmd)

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
        return self.operation(cmd)

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
        return self.operation(cmd)

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
        return self.operation(cmd)

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
        return self.operation(cmd)

    def restart(self):
        """
        Restart the device
        """
        return "".join(self._raw_restart().xpath(".//result/text()"))

    def automatic_download_software(
        self, version: Optional[str] = None
    ) -> types.SoftwareVersion:
        """
        Automatically download the requested software version.
        if the version is not provided, it defaults to the latest one.

        NOTE: This does not do the installation.
        This is usefull to download in anticipation of the upgrade.
        For automatic install, see `automatic_software_upgrade`
        """
        version_str = version
        try:
            versions = self.get_versions()
        except ServerError:
            raise Exception(
                "An error occured on the device while retrieving the device's versions. Be sure that the device can contact PaloAlto's servers."
            )
        sw_version = None
        if not version_str:
            sw_version = next((v for v in versions if v.latest), None)
        else:
            sw_version = next((v for v in versions if v.version == version_str), None)
        if not sw_version:
            self.logger.error(f"Version {version_str} not found")
            return exit(1)

        # Already downloaded: Nothing to do
        if sw_version.downloaded:
            self.logger.info(f"Version {sw_version.version} already downloaded")
            return sw_version

        # Download minor version first (required)
        base_version = next(
            v for v in versions if v.version == sw_version.base_minor_version
        )
        if not base_version.downloaded:
            self.logger.info(
                f"Launching download of minor version {base_version.version}"
            )
            job_id = self.download_software(base_version.version)
            if not job_id:
                raise Exception("Download has not started")
            job = self.wait_job_completion(job_id)
            if job.result != "OK":
                self.logger.debug(job)
                raise Exception(job.details)
            print(job.details)

        # Actually download the wanted version
        self.logger.info(f"Launching download of version {sw_version.version}")
        job_id = self.download_software(sw_version.version)
        if not job_id:
            raise Exception("Download has not started")
        job = self.wait_job_completion(job_id)
        if job.result != "OK":
            self.logger.debug(job)
            raise Exception(job.details)
        self.logger.info(job.details)
        return sw_version

    def automatic_software_upgrade(
        self, version: Optional[str] = None, install: bool = True, restart: bool = True
    ):
        """
        Automatically download and install the requested software version.
        if the version is not provided, it defaults to the latest one.

        NOTE: This does the software install and restart by default.
        If you only want to download, prefer to use `automatic_download_software` method,
        or set install=False. See the parameters for more information.

        install: install the software after the download
        restart: restart the device after the installation. This option is ignored if install=False

        """
        sw_version = self.automatic_download_software(version)
        if sw_version.current:
            self.logger.info(f"Version {sw_version.version} is already installed")
            return sw_version
        if not install:
            return sw_version
        # We may get the following error:
        # "Error: Upgrading from 10.2.4-h10 to 11.1.2 requires a content version of 8761 or greater and found 8638-7689."
        # This should never happen, we decided to report the error and handle this manually
        self.logger.info(f"Launching install of version {sw_version.version}")

        job_id = self.install_software(sw_version.version)
        if not job_id:
            self.logger.error("Install has not started")
            raise Exception("Install has not started")
        job = self.wait_job_completion(job_id)
        self.logger.info(job.details)

        # Do not restart if install failed
        if job.result != "OK":
            self.logger.error("Failed to install software version")
            return sw_version

        if restart:
            self.logger.info("Restarting the device")
            restart_response = self.restart()
            self.logger.info(restart_response)
        return sw_version

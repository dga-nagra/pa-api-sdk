from pa_api.utils import first
from pa_api.xmlapi.clients.operations.base import OperationProxy
from pa_api.xmlapi.utils import (
    Element,
)


class Config(OperationProxy):
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
        return self._request(cmd)

    def validate_changes(self):
        """
        Validated all the changes currently made
        """
        cmd = "<validate><full></full></validate>"
        return self._request(cmd)

    def _raw_get_push_scope(self, admin=None):
        """
        Gives detailed information about pending changes
        (e.g. xpath, owner, action, ...)
        """
        filter = f"<admin><member>{admin}</member></admin>" if admin else ""
        cmd = f"<show><config><push-scope>{filter}</push-scope></config></show>"
        return self._request(cmd)

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
        return self._request(cmd)

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
        return self._request(cmd)

    def pending_changes(self):
        """
        Result content is either 'yes' or 'no'
        """
        cmd = "<check><pending-changes></pending-changes></check>"
        return self._request(cmd)

    def save_config(self, name):
        """
        Create a named snapshot of the current configuration
        """
        cmd = f"<save><config><to>{name}</to></config></save>"
        return "\n".join(self._request(cmd).xpath(".//result/text()"))

    def save_device_state(self):
        """
        Create a snapshot of the current device state
        """
        cmd = "<save><device-state></device-state></save>"
        return "\n".join(self._request(cmd).xpath(".//result/text()"))

    def get_named_configuration(self, name):
        """
        Get the configuration from a named snapshot as an XML object
        """
        cmd = f"<show><config><saved>{name}</saved></config></show>"
        return self._request(cmd, remove_blank_text=False).xpath("./result/config")[0]

    def candidate_config(self) -> Element:
        """
        Get the configuration to be commited as an XML object
        """
        cmd = "<show><config><candidate></candidate></config></show>"
        return first(
            self._request(cmd, remove_blank_text=False).xpath("/response/result/config")
        )

    def running_config(self) -> Element:
        """
        Get the current running configuration as an XML object
        """
        cmd = "<show><config><running></running></config></show>"
        return first(
            self._request(cmd, remove_blank_text=False).xpath("/response/result/config")
        )

from pa_api.xmlapi.clients.operations.base import OperationProxy


class Lock(OperationProxy):
    def _lock_cmd(self, cmd, vsys, no_exception=False) -> bool:
        """
        Utility function for commands that tries to manipulate the lock
        on Panorama.
        """
        try:
            result = "".join(self._request(cmd, vsys=vsys).itertext())
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

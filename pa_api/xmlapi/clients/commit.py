from pa_api.xmlapi.clients.base import ClientProxy


class Commit(ClientProxy):
    def _request(
        self,
        cmd,
        method="POST",
        params=None,
        remove_blank_text=True,
        timeout=None,
    ):
        if params is None:
            params = {}
        params = {"cmd": cmd, **params}
        return self._base_request(
            "commit",
            method=method,
            params=params,
            remove_blank_text=remove_blank_text,
            timeout=timeout,
        )

    def commit_changes(self, force: bool = False):
        """
        Commit all changes
        """
        cmd = "<commit>{}</commit>".format("<force></force>" if force else "")
        return self._request(cmd)

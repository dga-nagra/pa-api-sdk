from typing import Optional

from pa_api.xmlapi import types
from pa_api.xmlapi.clients.base import ClientProxy
from pa_api.xmlapi.exceptions import ServerError


class Misc(ClientProxy):
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
            versions = self._client.operation.get_versions()
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
            job_id = self._client.operation.download_software(base_version.version)
            if not job_id:
                raise Exception("Download has not started")
            job = self._client.operation.job.wait_job_completion(job_id)
            if job.result != "OK":
                self.logger.debug(job)
                raise Exception(job.details)
            print(job.details)

        # Actually download the wanted version
        self.logger.info(f"Launching download of version {sw_version.version}")
        job_id = self._client.operation.download_software(sw_version.version)
        if not job_id:
            raise Exception("Download has not started")
        job = self._client.operation.job.wait_job_completion(job_id)
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

        job_id = self._client.operation.install_software(sw_version.version)
        if not job_id:
            self.logger.error("Install has not started")
            raise Exception("Install has not started")
        job = self._client.operation.job.wait_job_completion(job_id)
        self.logger.info(job.details)

        # Do not restart if install failed
        if job.result != "OK":
            self.logger.error("Failed to install software version")
            return sw_version

        if restart:
            self.logger.info("Restarting the device")
            restart_response = self._client.operation.restart()
            self.logger.info(restart_response)
        return sw_version

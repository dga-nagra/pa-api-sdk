from pydantic import AliasPath, ConfigDict, Field

from pa_api.xmlapi.types.utils import List, String, XMLBaseModel

from .devicegroup import DeviceGroup


class DeviceConfig(XMLBaseModel):
    name: String = Field(alias="@name")


class DeviceEntry(XMLBaseModel):
    name: String = Field(alias="@name")
    config: DeviceConfig = Field(alias="deviceconfig")
    device_groups: List[DeviceGroup] = Field(alias="device-group")


class Configuration(XMLBaseModel):
    """
    This is used to parse the output of the running configuration.
    """

    model_config = ConfigDict(extra="allow")

    urldb: String = Field(alias="@urldb")
    version: String = Field(alias="@version")
    detail_version: String = Field(alias="@detail-version")

    devices: List[DeviceEntry] = Field(validation_alias=AliasPath("devices", "entry"))

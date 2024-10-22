from typing import Optional

from pydantic import AliasPath, ConfigDict, Field

from pa_api.xmlapi.types.utils import List, String, XMLBaseModel

from .address import Address, AddressGroup
from .profiles import Profile
from .rules import RuleBase


class DeviceGroup(XMLBaseModel):
    """
    This is used to parse the output of the running configuration.
    """

    model_config = ConfigDict(extra="allow")

    name: String = Field(validation_alias="@name")
    description: String = ""

    devices: List[String] = Field(
        validation_alias=AliasPath("devices", "entry", "@name"), default_factory=list
    )
    profiles: Optional[Profile] = None
    addresses: List[Address] = Field(
        validation_alias=AliasPath("address", "entry"), default_factory=list
    )
    address_groups: List[AddressGroup] = Field(
        validation_alias=AliasPath("address-group", "entry"), default_factory=list
    )
    post_rulebase: Optional[RuleBase] = Field(
        validation_alias="post-rulebase", default=None
    )
    pre_rulebase: Optional[RuleBase] = Field(
        validation_alias="pre-rulebase", default=None
    )
    # applications: List[Application] = Field(
    #     validation_alias=AliasPath("application", "entry"), default_factory=list
    # )
    tags: List[String] = Field(
        validation_alias=AliasPath("tag", "member"), default_factory=list
    )

    def iter_rulebases(self):
        for rulebase in (self.pre_rulebase, self.post_rulebase):
            if rulebase is not None:
                yield rulebase

# Given a list of subnets,
# Find all NAT rules related to an address in the subnet


from typing import TYPE_CHECKING

from pydantic import Field

from pa_api.xmlapi.types.utils import List, String, XMLBaseModel

if TYPE_CHECKING:
    from pa_api.xmlapi.clients import Client


# https://docs.pydantic.dev/latest/concepts/alias/#aliaspath-and-aliaschoices
class CustomUrlCategory(XMLBaseModel):
    __resource_xpath__ = (
        "/config/devices/entry/device-group/entry/profiles/custom-url-category/entry"
    )

    name: str = Field(alias="@name")
    type: String
    members: List[String] = Field(alias="list", default_factory=list)

    @property
    def xpath(self):
        return f"{self.__resource_xpath__}[@name='{self.name}']"

    def add_static_member(self, client: "Client", member: str):
        client.configuration.create(f"{self.xpath}/list", f"<member>{member}</member>")

# Given a list of subnets,
# Find all NAT rules related to an address in the subnet


from pydantic import Field

from pa_api.xmlapi.types.utils import List, String, XMLBaseModel


# https://docs.pydantic.dev/latest/concepts/alias/#aliaspath-and-aliaschoices
class CustomUrlCategory(XMLBaseModel):
    name: str = Field(alias="@name")
    type: String
    members: List[String] = Field(alias="list")

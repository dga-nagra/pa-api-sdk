# Given a list of subnets,
# Find all NAT rules related to an address in the subnet


from pydantic import AliasPath, Field

from pa_api.xmlapi.types.utils import List, XMLBaseModel

from .custom_url_category import CustomUrlCategory


# https://docs.pydantic.dev/latest/concepts/alias/#aliaspath-and-aliaschoices
class Profile(XMLBaseModel):
    custom_url_categories: List[CustomUrlCategory] = Field(
        validation_alias=AliasPath("custom-url-category", "entry"), default_factory=list
    )
    # viruses: List[] = Field()
    # spywares: List[] = Field()
    # vulnerabilities: List[] = Field()
    # url_filtering: List[] = Field()
    # dos_protection: List[] = Field()

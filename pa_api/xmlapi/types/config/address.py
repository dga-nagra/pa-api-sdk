# Given a list of subnets,
# Find all NAT rules related to an address in the subnet

import string
from ipaddress import IPv4Network, IPv6Network, ip_network
from typing import Optional, Union

from pydantic import AliasChoices, AliasPath, Field
from pydantic.functional_validators import field_validator, model_validator
from typing_extensions import Self

from pa_api.xmlapi.types.utils import List, String, XMLBaseModel

IPNetwork = Union[IPv4Network, IPv6Network]


def get_ip_network(ip_netmask):
    try:
        if ip_netmask:
            return ip_network(ip_netmask, strict=False)
    except Exception:
        return None


# https://docs.pydantic.dev/latest/concepts/alias/#aliaspath-and-aliaschoices
class Address(XMLBaseModel):
    name: str = Field(validation_alias="@name")
    type: Optional[str] = None
    prefix: Optional[str] = None
    ip_netmask: Optional[str] = Field(
        alias="ip-netmask",
        validation_alias=AliasChoices(
            AliasPath("ip-netmask", "#text"),
            "ip-netmask",
        ),
        default=None,
    )
    ip_network: Optional[IPNetwork] = None
    ip_range: Optional[str] = Field(alias="ip-range", default=None)
    fqdn: Optional[String] = None
    tags: List[String] = Field(
        validation_alias=AliasPath("tag", "member"),
        default_factory=list,
    )

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v) -> List[str]:
        if not v:
            return []
        if not isinstance(v, list):
            return [v]
        return v

    @model_validator(mode="after")
    def validate_ip_network(self) -> Self:
        if self.ip_network is None:
            self.ip_network = get_ip_network(self.ip_netmask)
        if not isinstance(self.ip_network, (IPv4Network, IPv6Network)):
            self.ip_network = None
        return self

    @model_validator(mode="after")
    def validate_type(self) -> Self:
        address_type = None
        if self.prefix:
            address_type = "prefix"
        elif self.ip_netmask:
            address_type = "ip-netmask"
        elif self.ip_range:
            address_type = "ip-range"
        elif self.fqdn:
            address_type = "fqdn"
        self.type = address_type
        return self


# ======================================================
# Filtering tools


def take_until_marker(it, marker):
    for c in it:
        if c == marker:
            return
        yield c


def take_word(it):
    for c in it:
        if c in string.whitespace:
            return
        yield c


WORD_CHARSET = string.ascii_letters + string.digits + "_-"
AND = 1
OR = 2


def _parse_filter(it):
    node = []
    for c in it:
        if c in WORD_CHARSET:
            value = c
            for c in it:
                if c not in WORD_CHARSET:
                    if value == "or":
                        value = OR
                    elif value == "and":
                        value = AND
                    node.append(value)
                    break
                value += c
            else:  # We didn't break => We reached the end of the string
                node.append(value)
                return node
        if c == "(":
            subnode = _parse_filter(it)
            node.append(subnode)
        if c == ")":
            return node
        if c in ("'", '"'):
            value = "".join(take_until_marker(it, c))
            node.append(value)
    return node


def _dump_raw_node(node):
    for e in node:
        if e == AND:
            yield "and"
        elif e == OR:
            yield "or"
        elif isinstance(e, list):
            yield f"({' '.join(_dump_raw_node(e))})"
        else:
            yield repr(e)


def dump_raw_node(node):
    return " ".join(_dump_raw_node(node))


def parse_filter(text: str):
    it = iter(text)
    return _parse_filter(it)


# ======================================================


class DynamicFilter(XMLBaseModel):
    filter: String

    @property
    def sanitized_filter(self) -> str:
        raw_node = parse_filter(self.filter)
        filter = dump_raw_node(raw_node)
        return filter


class AddressGroup(XMLBaseModel):
    name: str = Field(validation_alias="@name")
    description: String = ""
    disable_override: Optional[bool] = Field(alias="disable-override", default=None)

    @property
    def type(self):
        if self.static_members and self.dynamic_members is not None:
            raise Exception("AddressGroup is both dynamic and static")
        if self.dynamic_members is not None:
            return "dynamic"
        return "static"

    static_members: List[String] = Field(alias="static", default_factory=list)
    dynamic_members: Optional[DynamicFilter] = Field(
        validation_alias="dynamic", default=None
    )

    tags: List[String] = Field(
        validation_alias=AliasPath("tag", "member"), default_factory=list
    )


# def find_addresses(tree):
#     # addresses_xml = tree.xpath(".//address/entry")
#     addresses_xml = tree.xpath("./devices/entry/device-group//address/entry")
#     address_objects = [Address.from_xml(n) for n in addresses_xml]

#     addresses = []
#     subnets = []
#     for a in address_objects:
#         network = a.ip_network
#         # We do not consider ip ranges for now
#         if not network:
#             continue
#         if network.prefixlen == network.max_prefixlen:
#             addresses.append(a)
#         else:
#             subnets.append(a)
#     return addresses, subnets

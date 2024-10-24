from typing import TYPE_CHECKING, Iterable, Literal, Optional, Union

from pydantic import AliasPath, ConfigDict, Field

from pa_api.xmlapi.types.utils import List, String, XMLBaseModel
from pa_api.xmlapi.utils import etree_tostring

if TYPE_CHECKING:
    from pa_api.xmlapi.clients import Client


class ProfileSetting(XMLBaseModel):
    groups: List[String] = Field(
        validation_alias=AliasPath("group", "member"), default_factory=list
    )


class Option(XMLBaseModel):
    disable_server_response_inspection: Optional[bool] = Field(
        validation_alias="disable-server-response-inspection", default=None
    )


class Target(XMLBaseModel):
    negate: Optional[bool] = None


class Security(XMLBaseModel):
    @property
    def xpath(self):
        return self.get_xpath()

    def get_xpath(self, rulebase=None):
        if rulebase is None:
            rulebase = "*[self::pre-rulebase or self::post-rulebase]"
        return f"/config/devices/entry/device-group/entry/{rulebase}/security/rules/entry[@uuid='{self.uuid}']"

    # def add_destination_member(self, client: "Client", member: str):
    #     return client.configuration.create(f"{self.xpath}/destination", f"<member>{member}</member>")

    def remove_destination_member(
        self, client: "Client", members: Union[str, Iterable[str]], rulebase=None
    ):
        # We cannot direclty edit members, we need to replace the whole object with its new configuration
        # pre-rulebase is required
        if isinstance(members, str):
            members = {members}
        if not isinstance(members, set):
            members_to_remove = set(members)
        if not members:
            return

        rule_xpath = self.get_xpath(rulebase)
        rule = client.configuration.get(rule_xpath).xpath("/response/result/entry")[0]
        destination = rule.xpath(".//destination")[0]
        nodes_to_remove = [
            m
            for m in destination.getchildren()
            if m.tag == "member" and m.text in members_to_remove
        ]
        for n in nodes_to_remove:
            destination.remove(n)
        client.configuration.update(rule_xpath, etree_tostring(rule))

    model_config = ConfigDict(extra="allow")

    name: String = Field(validation_alias="@name")
    uuid: String = Field(validation_alias="@uuid")
    disabled: Optional[bool] = None

    action: Literal["allow", "deny", "reset-client"]

    to: List[String] = Field(
        validation_alias=AliasPath("to", "member"), default_factory=list
    )
    from_: List[String] = Field(
        validation_alias=AliasPath("from", "member"), default_factory=list
    )
    sources: List[String] = Field(
        validation_alias=AliasPath("source", "member"), default_factory=list
    )
    destinations: List[String] = Field(
        validation_alias=AliasPath("destination", "member"), default_factory=list
    )
    source_users: List[String] = Field(
        validation_alias=AliasPath("source-user", "member"), default_factory=list
    )
    services: List[String] = Field(
        validation_alias=AliasPath("service", "member"), default_factory=list
    )
    applications: List[String] = Field(
        validation_alias=AliasPath("application", "member"), default_factory=list
    )

    description: String = ""
    categories: List[String] = Field(
        validation_alias=AliasPath("category", "member"), default_factory=list
    )
    tags: List[String] = Field(
        validation_alias=AliasPath("tag", "member"), default_factory=list
    )
    group_tag: Optional[String] = Field(validation_alias="group-tag", default=None)

    profile_settings: List[ProfileSetting] = Field(
        validation_alias=AliasPath("profile-settings"), default_factory=list
    )
    target: Optional[Target] = Field(validation_alias=AliasPath("target"), default=None)

    option: Optional[Option] = Field(default=None)
    rule_type: Optional[str] = Field(validation_alias="rule-type", default=None)
    negate_source: Optional[bool] = Field(
        validation_alias="negate-source", default=None
    )
    negate_destination: Optional[bool] = Field(
        validation_alias="negate-destination", default=None
    )
    log_settings: Optional[str] = Field(validation_alias="log-settings", default=None)
    log_start: Optional[bool] = Field(validation_alias="log-start", default=None)
    log_end: Optional[bool] = Field(validation_alias="log-end", default=None)
    icmp_unreachable: Optional[bool] = Field(
        validation_alias="icmp-unreachable", default=None
    )

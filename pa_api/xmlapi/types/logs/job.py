from datetime import time

from pydantic import Field

from pa_api.xmlapi.types.utils import Datetime, XMLBaseModel


class LogJob(XMLBaseModel):
    tenq: time
    tdeq: time
    tlast: time
    id: str
    status: str
    cached_logs: int = Field(alias="cached-logs")


class Log(XMLBaseModel):
    logid: int = Field(alias="@logid")
    start: Datetime
    time_received: Datetime
    time_generated: Datetime
    device_name: str
    type: str
    subtype: str
    action: str
    action_source: str
    serial: str
    vsys: str
    srcuser: str
    # Hosts
    src: str
    dst: str
    sport: str
    dport: str
    natsport: str
    natdport: str
    rule: str
    rule_uuid: str
    # Zones
    from_: str = Field(alias="from")
    to_: str = Field(alias="to")

    category_of_app: str
    category: str

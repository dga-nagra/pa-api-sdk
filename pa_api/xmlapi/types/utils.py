import json
import logging
import typing
from datetime import datetime
from types import new_class
from typing import Annotated, Any, Optional, TypeVar

from pydantic import (
    BaseModel,
    TypeAdapter,
)
from pydantic.functional_validators import (
    BeforeValidator,
    PlainValidator,
)
from typing_extensions import Self, TypedDict

from pa_api.utils import first
from pa_api.xmlapi.utils import el2dict

TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = f"%Y/%m/%d {TIME_FORMAT}"
DATETIME_MS_FORMAT = f"{DATETIME_FORMAT}.%f"
NoneType: type = type(None)

# if TYPE_CHECKING:
#     from pa_api.xmlapi.clients import Client


class XMLBaseModel(BaseModel):
    # raw_xml: Optional[Any] = None

    # @model_validator(mode="before")
    # @classmethod
    # def _get_raw_xml(cls, data, info: ValidationInfo):
    #     if isinstance(info.context, dict):
    #         raw_xml = info.context.get("raw_xml")
    #         if raw_xml is not None:
    #             data["raw_xml"] = raw_xml
    #     return data

    # @classmethod
    # def from_xml(cls, xml) -> Self:
    #     data = first(el2dict(xml).values())
    #     return cls.model_validate(data, context={"raw_xml": xml})

    # _client: Optional["Client"]
    # def bind_client(self, client: Optional["Client"]):
    #     self._client = client
    #     return self

    # @model_validator(mode="after")
    # def _auto_bind_client(self, info: ValidationInfo):
    #     client = None
    #     if isinstance(info.context, dict):
    #         client = info.context.get("client")
    #     self.bind_client(client)
    #     return self

    @classmethod
    def from_xml(cls, xml) -> Self:
        data = first(el2dict(xml).values())
        # context = {}
        # if client is not None:
        #     context["client"] = client
        return cls.model_validate(data)  # , context=context


def parse_datetime(d):
    try:
        if d is None or d in ("none", "Unknown"):
            return None
        try:
            return datetime.strptime(d, DATETIME_FORMAT)
        except Exception:
            return datetime.strptime(d, DATETIME_MS_FORMAT)
    except Exception as e:
        logging.debug(e)
        logging.debug(f"Failed to parse {d} as datetime")
        # print(d, type(d))
        raise
    return d


def parse_time(d):
    return datetime.strptime(d, TIME_FORMAT).time()


# https://docs.pydantic.dev/latest/concepts/types/#custom-types
# JobProgress = TypeAliasType('JobProgress', PlainValidator(parse_progress))
# Datetime = TypeAliasType(
#     "Datetime", Annotated[datetime, PlainValidator(parse_datetime)]
# )
Datetime = Annotated[datetime, PlainValidator(parse_datetime)]


def single_xpath(xml, xpath, parser=None, default=None):
    try:
        res = xml.xpath(xpath)
        res = first(res, None)
    except Exception:
        return default
    if res is None:
        return default
    if not isinstance(res, str):
        res = res.text
    if parser:
        res = parser(res)
    return res


pd = parse_datetime
sx = single_xpath


def mksx(xml):
    def single_xpath(xpath, parser=None, default=None):
        res = sx(xml, xpath, parser=parser, default=default)
        logging.debug(res)
        return res

    return single_xpath


def ensure_list(v: Any) -> typing.List[Any]:
    if v is None:
        return []
    if isinstance(v, dict) and len(v) == 1 and "member" in v:
        return ensure_list(v["member"])
    if isinstance(v, list):
        return v
    return [v]


# https://docs.pydantic.dev/latest/concepts/types/#generics
Element = TypeVar("Element", bound=Any)
# Similar to typing.List, but ensure to always return a list
List = Annotated[typing.List[Element], BeforeValidator(ensure_list)]


def xml_text(v: Any):
    if isinstance(v, dict) and "#text" in v:
        return v["#text"]
    return v


def ensure_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, dict):
        print(v)
        return v["#text"]
    return v


def validate_ip(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, dict):
        return v["@name"]
    return v


String = Annotated[str, BeforeValidator(ensure_str)]
Bool = Annotated[bool, BeforeValidator(xml_text)]
Ip = Annotated[str, BeforeValidator(validate_ip)]


def _xml2schema(values: list):
    types: typing.List[Any] = [
        t.__name__ for t in {type(v) for v in values if not isinstance(v, (dict, list))}
    ]
    list_values = [v for v in values if isinstance(v, list)]
    if list_values:
        types.append(_xml2schema([e for sublist in list_values for e in sublist]))
    dict_values = [v for v in values if isinstance(v, dict)]
    if dict_values:
        all_keys = {k for d in dict_values for k in d}
        dict_schema = {
            k: _xml2schema([d.get(k) for d in dict_values]) for k in all_keys
        }
        types.append(dict_schema)
    if not types:
        raise Exception("NO TYPE")
    if len(types) == 1:
        return types[0]
    return types


def _clean_key(k):
    return k.replace("@", "").replace("#", "")


def _slug(k):
    return _clean_key(k).replace("-", "_")


def _keyastypename(k):
    return "".join(p.title() for p in _clean_key(k).split("-"))


def _schematype(values: list, name: Optional[str] = None) -> type:
    if not name:
        name = "Dict"
    optional = None in values
    values = [v for v in values if v is not None]
    schema_types: typing.List[Any] = list(
        {type(v) for v in values if not isinstance(v, (dict, list))}
    )
    list_values = [v for v in values if isinstance(v, list)]
    if list_values:
        t = _schematype([e for sublist in list_values for e in sublist], name=name)
        schema_types.append(t)
    dict_values = [v for v in values if isinstance(v, dict)]
    if dict_values:
        all_keys = {k for d in dict_values for k in d}
        annotations = {
            _slug(k): _schematype(
                [d.get(k) for d in dict_values], name=_keyastypename(k)
            )
            for k in all_keys
        }
        t = new_class(
            name,
            (TypedDict,),
            None,
            lambda ns: ns.update({"__annotations__": annotations}),
        )
        schema_types.append(t)
    if not schema_types:
        return NoneType
        # raise Exception("NO TYPE")

    final_type = (
        schema_types[0] if len(schema_types) == 1 else typing.Union[tuple(schema_types)]
    )
    if optional:
        final_type = Optional[final_type]
    return final_type


def xml2schema(xml):
    """
    Similar to schematype function:
    The result is a recursive schema that can be dumped with json.
    """
    data = el2dict(xml)
    return _xml2schema([data])


def schematype(data, name: Optional[str] = None):
    """
    Recursively parse the data to infer the schema.
    The schema is returned as a type.

    We can dump the json schema using pydantic:
    TypeAdapter(schematype({"test": 5})).json_schema()
    """
    return _schematype([data], name=name)


def xml2schematype(xml):
    """
    Same to schematype function but takes an xml Element as parameter
    """
    name, data = first(el2dict(xml).items())
    return schematype(data, name)


def jsonschema(data, name=None, indent=4) -> str:
    ta = TypeAdapter(schematype(data, name))
    return json.dumps(ta.json_schema(), indent=indent)


def xml2jsonschema(data, indent=4) -> str:
    ta = TypeAdapter(xml2schematype(data))
    return json.dumps(ta.json_schema(), indent=indent)

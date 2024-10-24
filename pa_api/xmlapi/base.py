import logging

import requests

from pa_api.constants import PANORAMA_ERRORS, SUCCESS_CODE

from .exceptions import ServerError
from .utils import Element, detach, etree_fromstring, etree_tostring


def get_tree(
    host, api_key, remove_blank_text=True, verify=False, timeout=None, logger=None
):
    """
    This function returns the whole configuration of Panorama/the firewall
    as an XML object

    remove_blank_text:
        the response might contain extra white-spaces that will mess up
        the display. This option allows to automatically remove the extra white-spaces
    verify: Force the validation of https certificate
    """
    if logger is None:
        logger = logging
    res = requests.get(
        f"{host}/api?type=config&action=show&xpath=/config",
        headers={"X-PAN-KEY": api_key},
        verify=verify,
        timeout=timeout,
    )
    root_tree = etree_fromstring(res.content, remove_blank_text=remove_blank_text)
    try:
        tree = root_tree.xpath("/response/result/config")[0]
    except Exception:
        logger.warning("Response doesn't contains the config tag. Response:")
        logger.warning(etree_tostring(root_tree, pretty_print=True).decode()[:1000])
        raise Exception("Response doesn't contains the config tag. Check the logs")
    detach(tree)  # Remove the /response/result part
    return tree


def parse_msg_result(result: Element) -> str:
    """
    Parse the `msg` tag from Panorama response.
    This function always return the message as a single string
    """
    # Get the content from the default location
    msg = "".join(result.xpath("./msg/text()"))
    # Check another possible location
    if not msg:
        msg = "".join(result.xpath("./result/msg/text()"))
    if msg:
        return msg
    # Last possibility:
    # The message might be split in <line> elements inside of msg
    return "\n".join(result.xpath("./msg/line/text()"))


def _get_rule_use_cmd(device_group, position, rule_type, start_index, number) -> str:
    """
    This function return the `cmd` parameter to filter the data for rule usage.
    NOTE: These values are paged, we need to provide an offset and a limit.

    device_group: the device group that contains the rules and their usage data
    position: when the rule is used. Can be "pre" or "post"
    rule_type: One of the rule-type ("security", "pbf", "nat", "application-override")
    start_index: start index of the records to retrieve (aka "offset")
    number: number of records to retrieve (aka "limit")
    """
    # positions = ("pre", "post")
    return f"""<show><policy-app>
        <mode>get-all</mode>
        <filter>(rule-state eq 'any')</filter>
        <vsysName>{device_group}</vsysName>
        <position>{position}</position>
        <type>{rule_type}</type>
        <anchor>{start_index}</anchor>
        <nrec>{number}</nrec>
        <pageContext>rule_usage</pageContext>
    </policy-app></show>"""


def raw_request(
    url,
    type,
    method="GET",
    vsys=None,
    params=None,
    headers=None,
    remove_blank_text=True,
    verify=False,
    logger=None,
    parse=True,
    stream=None,
    timeout=None,
) -> Element:
    """
    This function is a wrapper around requests.method.
    It returns:
    - XML in case of success
    - a string with the message if a message is expected

    It does the heavy lifting when receiving a response from Panorama:
    - Data clean up
    - Conversion to XML
    - Status check and automaticly raise exception in case of error.
    """
    if logger is None:
        logger = logging
    query_params = {"type": type}
    if params:
        query_params = {**query_params, **params}
    if vsys is not None:
        query_params["vsys"] = vsys

    res = requests.request(
        method=method,
        url=url,
        params=query_params,
        headers=headers,
        verify=verify,
        stream=stream,
        timeout=timeout,
    )
    if not parse:
        return res
    content = res.content.decode()
    # try:
    #     tree = etree_fromstring(content, remove_blank_text=remove_blank_text)
    # except lxml.etree.XMLSyntaxError:
    #     print(content[:500])
    tree = etree_fromstring(content, remove_blank_text=remove_blank_text)
    status = tree.attrib["status"]
    code = int(tree.get("code", SUCCESS_CODE))
    if status == "error" or code < SUCCESS_CODE:
        logger.debug(content[:500])
        # print(content[:500])
        msg = parse_msg_result(tree)
        if msg:
            raise ServerError(msg)
        msg = PANORAMA_ERRORS.get(code)
        if msg is None:
            msg = f"Unknown error with code {code} occured"
        raise Exception(msg)

    # if tree.tag == "response":
    #     children = tree.getchildren()
    #     if len(children) == 1:
    #         tree = children[0]
    # if tree.tag == "result":
    #     children = tree.getchildren()
    #     if len(children) == 1:
    #         tree = children[0]
    return tree

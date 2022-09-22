"""Support for happi -
pcdshub.github.io/happi
"""


import re
import copy

from happi.item import HappiItem, EntryInfo  # type: ignore


class REManagerAPIZMQItem(HappiItem):
    zmq_control_addr = EntryInfo("ZMQ control address.", enforce=str, optional=False)
    zmq_info_addr = EntryInfo("ZMQ info address.", enforce=str, optional=False)
    kwargs = copy.copy(HappiItem.kwargs)
    kwargs.default = {"zmq_control_addr": "{{zmq_control_addr}}", "zmq_info_addr": "{{zmq_info_addr}}"}
    device_class = EntryInfo(default="bluesky_queueserver_api.zmq.REManagerAPI")


class REManagerAPIHTTPItem(HappiItem):
    http_server_uri = EntryInfo("HTTP server URI.", enforce=str, optional=False)
    http_auth_provider = EntryInfo("HTTP auth provider.", enforce=str, optional=False)
    kwargs = copy.copy(HappiItem.kwargs)
    kwargs.default = {"http_server_uri": "{{http_server_uri}}", "http_auth_provider": "{{http_auth_provider}}"}
    device_class = EntryInfo(default="bluesky_queueserver_api.http.REManagerAPI")

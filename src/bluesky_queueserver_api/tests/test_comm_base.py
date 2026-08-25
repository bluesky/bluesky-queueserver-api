"""Tests for ReManagerAPI_Base class in comm_base.py"""

import re

import pytest

from bluesky_queueserver_api.comm_base import ReManagerAPI_Base


def test_ReManagerAPI_Base_01():
    RM = ReManagerAPI_Base()
    assert RM.request_fail_exceptions_enabled is True

    RM.request_fail_exceptions_enabled = False
    assert RM.request_fail_exceptions_enabled is False


# fmt: off
@pytest.mark.parametrize("request_fail_exceptions", [True, False])
@pytest.mark.parametrize("response, success, msg", [
    (None, False, "Request failed: None"),
    (10, False, "Request failed: 10"),
    ([], True, ""),
    ([1, 2, 3], True, ""),
    ({}, True, ""),
    ({"success": True}, True, ""),
    ({"success": False}, False, "Request failed: (no error message)"),
    ({"success": False, "msg": "Error occurred"}, False, "Request failed: Error occurred"),
])
# fmt: on
def test_ReManagerAPI_Base_02(request_fail_exceptions, response, success, msg):
    RM = ReManagerAPI_Base(request_fail_exceptions=request_fail_exceptions)
    request = {"method": "test"}
    if success or not request_fail_exceptions:
        RM._check_response(request=request, response=response)
    else:
        with pytest.raises(RM.RequestFailedError, match=re.escape(msg)):
            RM._check_response(request=request, response=response)

        try:
            RM._check_response(request=request, response=response)
        except RM.RequestFailedError as ex:
            assert ex.response == response
            assert ex.request == request
        else:
            assert False, "Exception was not raised"

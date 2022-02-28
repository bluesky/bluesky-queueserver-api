import copy
import pprint
import pytest
import re

from bluesky_queueserver_api import BItem, BPlan, BFunc, BInst


# ======================================================================================
#                               BItem

# fmt: off
@pytest.mark.parametrize("item_args, item_kwargs", [
    (["plan", "count", ["det1", "det2"]], {}),
    (["plan", "count", ["det1", "det2"]], {"num": 10, "delay": 1}),
    (["plan", "count"], {"detectors": ["det1", "det2"], "num": 10, "delay": 1}),
    (["plan", "count"], {}),
    (["instruction", "queue_stop"], {}),
    (["function", "some_func"], {}),
])
# fmt: on
def test_BItem_01(item_args, item_kwargs):
    item_dict = {
        "item_type": item_args[0],
        "name": item_args[1],
        "args": item_args[2:],
        "kwargs": item_kwargs,
    }
    for k in ("args", "kwargs"):
        if not item_dict[k]:
            del item_dict[k]

    # Instantiate from parameters
    item = BItem(*item_args, **item_kwargs)
    assert item.to_dict() == item_dict, pprint.pformat(item.to_dict())

    assert item.item_type == item_dict["item_type"]
    assert item.name == item_dict["name"]
    assert item.args == item_dict.get("args", [])
    assert item.kwargs == item_dict.get("kwargs", {})
    assert item.meta == item_dict.get("meta", {})
    assert item.item_uid is None

    # Instantiate from another item
    item_copy = BItem(item)
    assert item_copy.to_dict() == item_dict, pprint.pformat(item.to_dict())

    # Instantiate from dictionary
    item_copy2 = BItem(item.to_dict())
    assert item_copy2.to_dict() == item_dict, pprint.pformat(item.to_dict())

    item2 = BItem("plan", "count")
    assert item2.args == []
    assert item2.kwargs == {}
    assert item2.meta == {}
    assert item2.dict_ref["args"] == []
    assert item2.dict_ref["kwargs"] == {}
    assert item2.dict_ref["meta"] == {}
    assert "args" not in item2.to_dict()
    assert "kwargs" not in item2.to_dict()
    assert "meta" not in item2.to_dict()


# fmt: off
@pytest.mark.parametrize("meta, item_uid", [
    ({"some": "metadata"}, None),
    ([{"first": "block"}, {"second": "block"}], None),
    (None, "some-item-uid"),
    ({"some": "metadata"}, "some-item-uid"),
])
# fmt: on
def test_BItem_02(meta, item_uid):
    item_dict = {
        "item_type": "plan",
        "name": "count",
        "args": [["det1", "det2"]],
        "kwargs": {"num": 10, "delay": 1},
    }

    if meta is not None:
        item_dict["meta"] = meta
    if item_uid is not None:
        item_dict["item_uid"] = item_uid

    item = BItem(item_dict)
    assert item.item_uid == item_dict.get("item_uid", None)
    assert item.meta == item_dict.get("meta", {})

    item2 = BItem(item)
    assert item2.item_uid == item_dict.get("item_uid", None)
    assert item2.meta == item_dict.get("meta", {})


def test_BItem_03():
    """
    Test that ``recognized_item_types`` property works as expected.
    """
    b = BItem("plan", "count")
    assert b.recognized_item_types == ("plan", "instruction", "function")


def test_BItem_04():
    """
    Test that ``__str__()`` and ``__repr__()`` works as expected.
    """
    b = BItem("plan", "count", ["det1", "det2"], num=10, delay=1)
    assert b.__str__() == b.to_dict().__str__()
    assert b.__repr__() == b.to_dict().__repr__()


def test_BItem_05():
    """
    Test that ``__str__()`` and ``__repr__()`` works as expected.
    """
    b1 = BItem("plan", "count", ["det1", "det2"], num=10, delay=1)
    b1.meta = {"some": "parameter"}
    b1_dict = copy.deepcopy(b1.to_dict())

    # Create a copy, change a parameter in the copy and make sure the original was not changed
    b2 = BItem(b1)
    b2.args = [["det1"]]
    assert b2.args == [["det1"]]
    assert b1.to_dict() == b1_dict

    # Verify that 'to_dict' returns a copy
    b1_dict_copy = b1.to_dict()
    b1_dict_copy["args"] == [["det1"]]
    assert b1.to_dict() == b1_dict

    # Verify that 'args', 'kwargs' and 'meta' return references
    b1_args = b1.args
    b1_args[0] = ["det1"]
    assert b1.to_dict() != b1_dict

    b1_kwargs = b1.kwargs
    b1_kwargs["num"] = 50
    assert b1.to_dict() != b1_dict

    b1_meta = b1.meta
    b1_meta["some"] = "new_parameter"
    assert b1.to_dict() != b1_dict

    # Verify that setting 'args', 'kwargs' and 'meta' include copying the data
    b1_args = [["det4"]]
    b1.args = b1_args
    b1.args[0] = [["det1"]]
    assert b1_args == [["det4"]]

    b1_kwargs = {"num": 7}
    b1.kwargs = b1_kwargs
    b1.kwargs["num"] = 5
    assert b1_kwargs == {"num": 7}

    b1_meta = {"num": 7}
    b1.meta = b1_meta
    b1.meta["num"] = 5
    assert b1_meta == {"num": 7}

    # Verify that 'dict_ref' allows access to the internal dictionary
    b1.dict_ref["args"] = [["det2"]]
    assert b1.to_dict() != b1_dict


# fmt: off
@pytest.mark.parametrize("item_args, item_kwargs, error_type, msg", [
    ([], {}, KeyError, "'item_type' and 'item_name' are missing in constructor arguments"),
    (["plan"], {}, KeyError, "'item_name' is missing in constructor arguments"),
    ([10, "count"], {}, TypeError, "Item type 10 is not a string: (<class 'int'>)"),
    (["plan", 10], {}, TypeError, "Item name 10 is not a string: (<class 'int'>)"),
    ([{"name": "count"}], {}, KeyError,
     "Required 'item_type' key is not found in the item dictionary {'name': 'count'}"),
    ([{"item_type": "plan"}], {}, KeyError,
     "Required 'name' key is not found in the item dictionary {'item_type': 'plan'}"),
    ([{"name": "count"}], {}, KeyError,
     "Required 'item_type' key is not found in the item dictionary {'name': 'count'}"),
    ([{"item_type": 10, "name": "count"}], {}, TypeError, "Item type 10 is not a string: (<class 'int'>)"),
    ([{"item_type": "plan", "name": 10}], {}, TypeError, "Item name 10 is not a string: (<class 'int'>)"),
    ([{"item_type": "unknown", "name": "count"}], {}, ValueError,
     "Unsupported item type: 'unknown'. Supported types: ('plan', 'instruction', 'function')"),
])
# fmt: on
def test_BItem_06_failing(item_args, item_kwargs, error_type, msg):
    """
    Initialization of ``BItem``: failing cases of initialization by passing args and kwargs
    to the constructor. Test exception types and error messages.
    """
    with pytest.raises(error_type, match=re.escape(msg)):
        BItem(*item_args, **item_kwargs)


# fmt: off
@pytest.mark.parametrize("item_type, name, args, kwargs, meta, item_uid, error_type, msg", [
    (None, "count", None, None, None, None, KeyError,
     "Required 'item_type' key is not found in the item dictionary {'name': 'count'}"),
    (10, "count", None, None, None, None, TypeError, "Item type 10 is not a string: (<class 'int'>)"),
    ("unknown", "count", None, None, None, None, ValueError,
     "Unsupported item type: 'unknown'. Supported types: ('plan', 'instruction', 'function')"),
    ("plan", None, None, None, None, None, KeyError,
     "Required 'name' key is not found in the item dictionary {'item_type': 'plan'}"),
    ("plan", 10, None, None, None, None, TypeError, "Item name 10 is not a string: (<class 'int'>)"),
    ("plan", "", None, None, None, None, ValueError, "Item name is an empty string"),
    ("plan", "count", "invalid", None, None, None, TypeError,
     "Item args 'invalid' must be iterable: (<class 'str'>)"),
    ("plan", "count", 10, None, None, None, TypeError,
     "Item args 10 must be iterable: (<class 'int'>)"),
    ("plan", "count", None, "invalid", None, None, TypeError,
     "Item kwargs 'invalid' must be a mapping: (<class 'str'>)"),
    ("plan", "count", None, 10, None, None, TypeError,
     "Item kwargs 10 must be a mapping: (<class 'int'>)"),
    ("plan", "count", None, None, "invalid", None, TypeError,
     "Item metadata 'invalid' must be a mapping or an iterable: (<class 'str'>)"),
    ("plan", "count", None, None, 10, None, TypeError,
     "Item metadata 10 must be a mapping or an iterable: (<class 'int'>)"),
    ("plan", "count", None, None, [{"param": 10}, 10], None, TypeError,
     "One of the elements of item metadata list is not a mapping (<class 'int'>)"),
    ("plan", "count", None, None, None, 10, TypeError, "Item UID 10 is not a string: (<class 'int'>)"),
    ("plan", "count", None, None, None, [], TypeError, "Item UID [] is not a string: (<class 'list'>)"),
    ("plan", "count", None, None, None, "", ValueError, "Item UID is an empty string"),
])
# fmt: on
def test_BItem_07_failing(item_type, name, args, kwargs, meta, item_uid, error_type, msg):
    """
    Initialization of ``BItem``: failing cases of initialization and setting properties.
    Test initialization using constructor, ``from_dict`` property, setting
    ``item_type``, ``name``, ``args``, ``kwargs``, ``item_uid`` and ``meta`` properties.
    Test the exception types and error messages.
    """
    item_dict = {}
    if item_type is not None:
        item_dict["item_type"] = item_type
    if name is not None:
        item_dict["name"] = name
    if args is not None:
        item_dict["args"] = args
    if kwargs is not None:
        item_dict["kwargs"] = kwargs
    if meta is not None:
        item_dict["meta"] = meta
    if item_uid is not None:
        item_dict["item_uid"] = item_uid

    with pytest.raises(error_type, match=re.escape(msg)):
        BItem(item_dict)

    with pytest.raises(error_type, match=re.escape(msg)):
        b = BItem("plan", "count")
        b.from_dict(item_dict)

    with pytest.raises(error_type, match=re.escape(msg)):
        b = BItem("plan", "count")
        for k, v in item_dict.items():
            if k == "item_type":
                b.item_type = v
            if k == "name":
                b.name = v
            if k == "args":
                b.args = v
            if k == "kwargs":
                b.kwargs = v
            if k == "meta":
                b.meta = v
            if k == "item_uid":
                b.item_uid = v
        # There are two tests that will not raise exceptions, because they happen only during
        #   initialization of 'BItem'. So we just raise exceptions so that the test works.
        if ("Required 'item_type' key is not found" in msg) or ("Required 'name' key is not found" in msg):
            raise error_type(msg)


def test_BPlan_BInst_BFunc_01():
    """
    Tests for BPlan, BInst and BFunc: ``recognized_item_types`` property
    """
    bp = BPlan("plan", "count")
    assert bp.recognized_item_types == ["plan"]

    bi = BInst("instruction", "queue_stop")
    assert bi.recognized_item_types == ["instruction"]

    bf = BFunc("function", "test_func")
    assert bf.recognized_item_types == ["function"]


# fmt: off
@pytest.mark.parametrize("object_type, item_args, item_kwargs", [
    (BPlan, ["count", ["det1", "det2"]], {}),
    (BPlan, ["count", ["det1", "det2"]], {"num": 10, "delay": 1}),
    (BPlan, ["count"], {"detectors": ["det1", "det2"], "num": 10, "delay": 1}),
    (BPlan, ["count"], {}),
    (BInst, ["queue_stop"], {}),
    (BInst, ["test_func"], {}),
])
# fmt: on
def test_BPlan_BInst_BFunc_02(object_type, item_args, item_kwargs):
    """
    Tests for BPlan, BInst and BFunc: initialization and copying
    """
    item_type = {BPlan: "plan", BInst: "instruction", BFunc: "function"}[object_type]
    item_dict = {
        "item_type": item_type,
        "name": item_args[0],
        "args": item_args[1:],
        "kwargs": item_kwargs,
    }
    for k in ("args", "kwargs"):
        if not item_dict[k]:
            del item_dict[k]

    # Instantiate from parameters
    item = object_type(*item_args, **item_kwargs)
    assert item.to_dict() == item_dict, pprint.pformat(item.to_dict())

    assert item.item_type == item_dict["item_type"]
    assert item.name == item_dict["name"]
    assert item.args == item_dict.get("args", [])
    assert item.kwargs == item_dict.get("kwargs", {})
    assert item.meta == item_dict.get("meta", {})
    assert item.item_uid is None

    # Instantiate from another item
    item_copy = object_type(item)
    assert item_copy.to_dict() == item_dict, pprint.pformat(item.to_dict())

    # Instantiate from dictionary
    item_copy2 = object_type(item.to_dict())
    assert item_copy2.to_dict() == item_dict, pprint.pformat(item.to_dict())


# fmt: off
@pytest.mark.parametrize("object_type, item_type, name, error_type, msg1, msg2", [
    (BPlan, "instruction", "queue_stop", ValueError,
     "Item 'plan' can not be initialized from a dictionary which represents 'instruction'",
     "Unsupported item type: 'instruction'. Supported types: ['plan']"),
    (BFunc, "instruction", "queue_stop", ValueError,
     "Item 'function' can not be initialized from a dictionary which represents 'instruction'",
     "Unsupported item type: 'instruction'. Supported types: ['function']"),
    (BInst, "plan", "count", ValueError,
     "Item 'instruction' can not be initialized from a dictionary which represents 'plan'",
     "Unsupported item type: 'plan'. Supported types: ['instruction']"),
])
# fmt: on
def test_BPlan_BInst_BFunc_03_failing(object_type, item_type, name, error_type, msg1, msg2):
    """
    Tests for BPlan, BInst and BFunc: failing cases of initialization.
    """
    item_dict = {}
    if item_type is not None:
        item_dict["item_type"] = item_type
    if name is not None:
        item_dict["name"] = name

    with pytest.raises(error_type, match=re.escape(msg1)):
        object_type(item_dict)

    with pytest.raises(error_type, match=re.escape(msg1.replace("dictionary", "class object"))):
        object_type(BItem(item_dict))

    with pytest.raises(error_type, match=re.escape(msg2)):
        b = object_type("some_name")
        b.from_dict(item_dict)

    with pytest.raises(error_type, match=re.escape(msg2)):
        b = object_type("some_name")
        for k, v in item_dict.items():
            if k == "item_type":
                b.item_type = v
            if k == "name":
                b.name = v

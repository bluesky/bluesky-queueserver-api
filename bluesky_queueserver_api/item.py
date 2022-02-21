from collections.abc import Mapping, Iterable
import copy


class BItem:
    """
    A helper class that generates dictionary with queue item parameters. The class
    performs validation of values to ensure that the dictionary is formatted correctly.
    A queue item can be represented as a plain Python dictionary. Using this class
    to represent is queue items is optional.

    The item can be instantiated from a dictionary that contains valid item parameters
    or by passing item type, item name, args and kwargs or from another ``BItem`` object.
    The class implements public properties that allow to access all important item
    parameters, such as ``item_type``, ``name``, ``args``, ``kwargs``, ``meta``
    and ``item_uid``.

    Parameters
    ----------
    *args: list
        The first two arguments are required and should represent item type (allowed
        values are ``'plan'``, ``'instruction'`` and ``'function`'') and item name
        (name of the plan, instruction or function represented as a string). The remaining
        arguments are optional and represent args of the plan or function. Alternatively,
        an item may be instantiated from a valid dictionary of item parameters or another
        item object. In this case the constructor should be passed a single argument that
        contains the dictionary or the object and no keyword arguments.
    **kwargs: dict
        Keyword arguments of the plan or function.

    Raises
    ------
    KeyError, ValueError, TypeError
        Missing parameter or invalid parameter types or values

    Examples
    --------

    .. code-block:: python

        plan1 = BItem("plan", "count", ["det1", "det2"], num=10, delay=1)
        plan2 = BItem(plan1)  # Creates a copy of a plan
        plan3 = BItem({
            "item_type": "plan",
            "name": "count",
            "args": [["det1", "det2]],
            "kwargs": {"num": 10, "delay": 1}
        })

        item_type = plan1.item_type  # Require, always set
        item_name = plan1.name  # Required, always set
        item_args = plan1.args  # Optional, [] if not set
        item_kwargs = plan1.kwargs  # Optional, {} if not set
        item_uid = plan1.item_uid  # Usually set by the server, None if not set
        item_meta = plan1.meta  # Optional, {} if not set

        # Convert 'plan1' into 'queue_stop' instruction (properties are writable)
        plan1.item_type = "instruction"
        plan1.name = "queue_stop"
        plan1.args = []
        plan1.kwargs = {}
        plan1.meta = {}

        plan1_dict = plan1.to_dict()  # Returns a copy of the internal dictionary
        plan2.from_dict(plan1_dict)  # Makes 'plan2' a copy of 'plan1'
        plan2.from_dict(plan1)  # Works exactly the same

        # Access to internal dictionary
        dict_ref = plan3.dict_ref
        dict_ref["args"] = [["det1"]]

    """

    _recognized_item_types = ("plan", "instruction", "function")

    def __init__(self, *args, **kwargs):
        # TODO: add validation code for the plan dictionary, probably based on ``jsonschema``.
        #       Plan validation is important for item dictionaries created in user code.

        if (len(args) == 1) and not kwargs and isinstance(args[0], Mapping):
            # The special case when the constructor accepts a dictionary of parameters
            self._item_dict = self._validate_item_dict(args[0])
        elif (len(args) == 1) and not kwargs and isinstance(args[0], BItem):
            # The special case when the constructor accepts another BItem object
            self._item_dict = args[0].to_dict()
        else:
            if len(args) == 0:
                raise KeyError("'item_type' and 'item_name' are missing in constructor arguments")
            if len(args) == 1:
                raise KeyError("'item_name' is missing in constructor arguments")

            item_type = args[0]
            item_name = args[1]

            self._item_dict = {}
            self.item_type = item_type
            self.name = item_name
            if len(args) > 2:
                self.args = list(args[2:])
            if kwargs:
                self.kwargs = kwargs

    def _validate_item_dict(self, item_dict):
        """
        Perform validation of item dictionary. Convert mappings to dicts and iterables to lists.
        Returns the modified copy of the dictionary. The original dictionary is not modified.
        """
        if not isinstance(item_dict, Mapping):
            raise TypeError(f"Item dictionary is not a mapping: {type(item_dict)!r}")
        item_dict = copy.deepcopy(dict(item_dict))

        # Required keys
        for k in ("item_type", "name"):
            if k not in item_dict:
                raise KeyError(f"Required {k!r} key is not found in the item dictionary {item_dict}")

        self._validate_item_type(item_dict["item_type"])
        self._validate_name(item_dict["name"])
        if "item_uid" in item_dict:
            self._validate_item_uid(item_dict["item_uid"])

        valid_map = {"args": self._validate_args, "kwargs": self._validate_kwargs, "meta": self._validate_meta}
        for k, f in valid_map.items():
            if k in item_dict:
                item_dict[k] = f(item_dict[k])

        return item_dict

    def _validate_item_type(self, item_type):
        """
        Check that type name is a string that matches one of the supported item types.
        """
        if not isinstance(item_type, str):
            raise TypeError(f"Item type {item_type!r} is not a string: ({type(item_type)!r})")
        if item_type not in list(self.recognized_item_types):  # list() needed in Python 3.7, 3.8
            raise ValueError(
                f"Unsupported item type: {item_type!r}. Supported types: {self.recognized_item_types}"
            )

    def _validate_name(self, name):
        """
        Check that item name is a non-empty string.
        """
        if not isinstance(name, str):
            raise TypeError(f"Item name {name!r} is not a string: ({type(name)!r})")
        if not name:
            raise ValueError("Item name is an empty string")

    def _validate_item_uid(self, item_uid):
        """
        Check that item uid is a non-empty string.
        """
        if not isinstance(item_uid, str):
            raise TypeError(f"Item UID {item_uid!r} is not a string: ({type(item_uid)!r})")
        if not item_uid:
            raise ValueError("Item UID is an empty string")

    def _validate_args(self, item_args):
        """
        Check that 'args' is iterable and convert it to a list. Returns the list.
        """
        if not isinstance(item_args, Iterable) or isinstance(item_args, str):
            raise TypeError(f"Item args {item_args!r} must be iterable: ({type(item_args)!r})")
        return list(item_args)

    def _validate_kwargs(self, item_kwargs):
        """
        Check that 'kwargs' is a mapping and convert it to dict. Returns the dict.
        """
        if not isinstance(item_kwargs, Mapping):
            raise TypeError(f"Item kwargs {item_kwargs!r} must be a mapping: ({type(item_kwargs)!r})")
        return dict(item_kwargs)

    def _validate_meta(self, item_meta):
        """
        Check that metadata is a mapping or an iterable. If it is a mapping, then it is converted
        to a dict. If it is an iterable, then it is converted to a list. For each element of the list
        the function checks if it is a mapping and converts it to a dict. Returns the list or a dict.
        """
        if isinstance(item_meta, Mapping):
            item_meta = dict(item_meta)
        elif isinstance(item_meta, Iterable) and not isinstance(item_meta, str):
            item_meta = list(item_meta)
            for md in item_meta:
                if not isinstance(md, Mapping):
                    raise TypeError(f"One of the elements of item metadata list is not a mapping ({type(md)})")
                md = dict(md)
        else:
            raise TypeError(f"Item metadata {item_meta!r} must be a mapping or an iterable: ({type(item_meta)!r})")
        return item_meta

    @classmethod
    @property
    def recognized_item_types(cls):
        """
        The read-only property returns the list of item types recognized by the queue
        server. Item types include ``plan``, ``instruction`` and ``function``. This is a class
        property, which could be accessed as ``BItem.recognized_item_types``.
        """
        return cls._recognized_item_types

    @property
    def item_type(self):
        """
        The property for read-write access to the item type. Item type is a mandatory
        item parameter represented as a string from the list retured by ``BPlan.recognized_item_types``.

        Raises
        ------
        ValueError
            Raised if the new value for item type is not in the list of recognized item types.
        """
        return self._item_dict["item_type"]

    @item_type.setter
    def item_type(self, item_type):
        self._validate_item_type(item_type)
        self._item_dict["item_type"] = item_type

    @property
    def name(self):
        """
        The property for read-write access to the item name. Item name is a mandatory item parameter
        that holds a string with the name of the existing plan, instruction or function.

        Raises
        ------
        TypeError
            Raised if the new item name is not a string.
        ValueError
            Raised if the new item name is an empty string.
        """
        return self._item_dict["name"]

    @name.setter
    def name(self, name):
        self._validate_name(name)
        self._item_dict["name"] = name

    @property
    def args(self):
        """
        The read-write property sets or gets the copy of the list of item args. This is an optional parameter.
        An empty list is returned if args are not set.

        Raises
        ------
        TypeError
            Raised if the new value is not a list.
        """
        return copy.deepcopy(self._item_dict.get("args", []))

    @args.setter
    def args(self, item_args):
        item_args = self._validate_args(item_args)
        self._item_dict["args"] = copy.deepcopy(item_args)

    @property
    def kwargs(self):
        """
        The read-write property sets or gets the copy of the dictionary of item kwargs.
        This is an optional parameter. An empty dictionary is returned if kwargs are not set.

        Raises
        ------
        TypeError
            Raised if the new value is not a dictionary.
        """
        return copy.deepcopy(self._item_dict.get("kwargs", {}))

    @kwargs.setter
    def kwargs(self, item_kwargs):
        item_kwargs = self._validate_kwargs(item_kwargs)
        self._item_dict["kwargs"] = copy.deepcopy(item_kwargs)

    @property
    def item_uid(self):
        """
        The property for read-write access to the item uid. This is an optional parameter, which
        is typically not set by the user. In most cases the server will overwrite the UID set
        by the user. ``None`` is returned if UID is not set.

        Raises
        ------
        TypeError
            Raised if the new value is not a string.
        """
        return self._item_dict.get("item_uid", None)

    @item_uid.setter
    def item_uid(self, item_uid):
        self._validate_item_uid(item_uid)
        self._item_dict["item_uid"] = item_uid

    @property
    def meta(self):
        """
        The read-write property that sets or gets the copy of item metadata. Metadata is currenly
        used only for plans. Metadata set for instructions and functions is ignored. This is
        an optional parameter. An empty dictionary is returned if kwargs are not set. Metadata
        may be represented as a dictionary or a list of dictionaries. The dictionaries in the list
        are merged into a single dictionary before metadata is passed to the plan.

        Raises
        ------
        TypeError
            Raised if the new value is not a dictionary.
        """
        return copy.deepcopy(self._item_dict.get("meta", {}))

    @meta.setter
    def meta(self, meta):
        meta = self._validate_meta(meta)
        self._item_dict["meta"] = copy.deepcopy(meta)

    def to_dict(self):
        """
        The method returns the copy of the dictionary with item parameters, which is ready to be
        passed to the server.
        """
        return copy.deepcopy(self._item_dict)

    def from_dict(self, item_dict):
        """
        The method copies item parameters from a dictionary. All the existing item parameters are deleted.
        """
        if isinstance(item_dict, BItem):
            dict_to_copy = item_dict.to_dict()
        elif isinstance(item_dict, Mapping):
            dict_to_copy = self._validate_item_dict(item_dict)
        else:
            raise TypeError(
                f"Unsupported type {type(item_dict)!r} of parameter ``item_dict``: "
                "BItem object or Mapping is accepted."
            )
        self._item_dict.clear()
        self._item_dict.update(dict_to_copy)

    @property
    def dict_ref(self):
        """
        The property returns reference to iternal item dictionary.
        """
        return self._item_dict

    def __str__(self):
        return self._item_dict.__str__()

    def __repr__(self):
        return self._item_dict.__repr__()


class _BItemSpecialized(BItem):
    """
    The helper class for creating and maintaining a dictionary with the description of an item
    that represents a plan (``BPlan``), instruction (``BInst``) or function (``BFunc``).
    The class functionality is similar to ``BItems``, but specified for operations with
    particular type of items.

    Parameters
    ----------
    *args: list
        (name of the plan, instruction or function represented as a string). The remaining
        arguments are optional and represent args of the plan or function. Alternatively,
        an item may be instantiated from a valid dictionary of item parameters or another
        object that represent an item of matching type. Then the constructor receive a single
        argument that contains the dictionary or the item object and no keyword arguments.
    **kwargs: dict
        Keyword arguments of the plan or function.

    Raises
    ------
    KeyError, ValueError, TypeError
        Missing parameter or invalid parameter types or values

    Examples
    --------

    .. code-block:: python

        plan1 = BPlan("count", ["det1", "det2"], num=10, delay=1)
        inst1 = BInst("queue_stop")
        func1 = BFunc("custom_func", 10)

        plan2 = BPlan(plan1.to_dict())  # Copy of 'plan'
        plan2 = BPlan(plan1)  # Works exactly the same

        # Initialization from items of another type always fails
        BPlan(func1.to_dict())  # Fails
        BPlan(inst1)  # Fails
        plan1.from_dict(func1.to_dict())  # Fails
        plan1.from_dict(inst1)  # Fails

        # BItem can be initialized from specialized item objects
        item = BItem(inst1.to_dict)  # Works
        item = BItem(inst1)  # Works

        # The following sequence works, because item type is correct
        item1 = BItem(plan1)  # 'item1' is still a plan
        plan3 = BPlan(item1)  # Initialize a plan object with another plan object
    """

    def __init__(self, *args, **kwargs):
        # The class serves as a base class for ``BPlan``, ``BInst`` and ``BFunc`` classes.
        # It cannot be instantiated or used by itself.
        init_from_dictionary = False
        if (len(args) == 1) and not kwargs and isinstance(args[0], Mapping):
            # The special case when the constructor accepts a dictionary of parameters
            if "item_type" not in args[0]:
                raise KeyError(f"'item_type' key is not found in item parameter dictionary {args[0]}")
            if args[0]["item_type"] != self._class_item_type:
                raise ValueError(
                    f"Item {self._class_item_type!r} can not be initialized "
                    f"from a dictionary which represents {args[0]['item_type']!r}"
                )
            init_from_dictionary = True

        elif (len(args) == 1) and not kwargs and isinstance(args[0], BItem):
            # The special case when the constructor accepts another BItem object
            if args[0].item_type != self._class_item_type:
                raise ValueError(
                    f"Item {self._class_item_type!r} can not be initialized "
                    f"from a class object which represents {args[0].item_type!r}"
                )
            init_from_dictionary = True

        if init_from_dictionary:
            super().__init__(*args, **kwargs)
        else:
            super().__init__(self._class_item_type, *args, **kwargs)


class BPlan(_BItemSpecialized):
    _class_item_type = "plan"
    _recognized_item_types = [_class_item_type]
    __doc__ = _BItemSpecialized.__doc__


class BInst(_BItemSpecialized):
    _class_item_type = "instruction"
    _recognized_item_types = [_class_item_type]
    __doc__ = _BItemSpecialized.__doc__


class BFunc(_BItemSpecialized):
    _class_item_type = "function"
    _recognized_item_types = [_class_item_type]
    __doc__ = _BItemSpecialized.__doc__

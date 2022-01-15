from collections.abc import Mapping, Iterable
import copy


class BItem:
    """
    A helper class that generates dictionary with queue item parameters. The class
    performs validation of values to ensure that the dictionary is formatted correctly.
    A queue item can be represented as a plain Python dictionary. Using this class
    to represent is queue items is optional.

    The item can be instantiated from a dictionary that contains valid item parameters
    or by passing item type, item name, args and kwargs. The class implements public
    properties that allow to access all important item parameters, such as ``item_type``,
    ``name``, ``args``, ``kwargs``, ``meta`` and ``item_uid``.

    Parameters
    ----------
    *args: list
        The first two arguments are required and should represent item type (allowed
        values are ``'plan'``, ``'instruction'`` and ``'function`'') and item name
        (name of the plan, instruction or function represented as a string). The remaining
        arguments are optional and represent args of the plan or function.
        Alternatively, if the item is instantiated from a valid dictionary of item parameters,
        the constructor should be passed a single argument that contains the dictionary and
        no keyword arguments.
    **kwargs: dict
        Keyword arguments of the plan or function.

    Raises
    ------
    ValueError, TypeError
        Invalid types or values of parameters
    """

    _recognized_item_types = ("plan", "instruction", "function")

    def __init__(self, *args, **kwargs):
        # TODO: add validation code for the plan dictionary, probably based on ``jsonschema``.
        #       Plan validation is important for item dictionaries created in user code.

        if (len(args) == 1) and not kwargs and isinstance(args[0], Mapping):
            # The special case when the constructor accepts a dictionary of parameters
            self._item_dict = copy.deepcopy(dict(args[0]))
        else:
            if len(args) == 0:
                raise ValueError("Parameters 'item_type' and 'item_name' are missing in function call")
            if len(args) == 1:
                raise ValueError("Parameter 'item_name' are missing in function call")

            item_type = args[0]
            item_name = args[1]

            self._item_dict = {}
            self.item_type = item_type
            self.name = item_name
            if len(args) > 2:
                self.args = list(args[2:])
            if kwargs:
                self.kwargs = kwargs

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
        if item_type not in self.recognized_item_types:
            raise ValueError(
                f"Unrecognized item type: {item_type!r}. Supported item types: {self.recognized_item_types}"
            )
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
        if not isinstance(name, str):
            raise TypeError(f"Item name {name!r} has type {type(name)!r}. Supported type: 'str'")
        if not name:
            raise ValueError("Item name is an empty string")
        self._item_dict["name"] = str(name)

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
        if not isinstance(item_args, Iterable) or isinstance(item_args, str):
            raise TypeError(f"Item args type is {type(item_args)!r}, which is not iterable")
        self._item_dict["args"] = copy.deepcopy(list(item_args))

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
        if not isinstance(item_kwargs, Mapping):
            raise TypeError(f"Item kwargs type is {type(item_kwargs)!r}, which is not a mapping")
        self._item_dict["kwargs"] = copy.deepcopy(dict(item_kwargs))

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
        if not isinstance(item_uid, str):
            raise TypeError(f"Item item_uid type is {type(item_uid)!r}, which is not a string")
        self._item_dict["item_uid"] = str(item_uid)

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
        if isinstance(meta, Mapping):
            meta = dict(meta)
        elif isinstance(meta, Iterable) and not isinstance(meta, str):
            meta = list(meta)
            for md in meta:
                if not isinstance(md, Iterable):
                    raise (f"One of the elements of 'meta' list is not a dictionary ({type(md)})")
                md = dict(md)
        else:
            raise TypeError(
                f"Metadata type is {type(meta)!r}, which is not a dictionary or a list of dictionaries"
            )
        self._item_dict["meta"] = copy.deepcopy(meta)

    def to_dict(self):
        """
        The method returns the copy of the dictionary with item parameters, which is ready to be
        passed to the server.
        """
        return copy.deepcopy(self._item_dict)

    def from_dict(self, item_dict):
        """
        The method copies item parameters from the dictionary. All the existing item parameters are deleted.
        """
        self._item_dict = copy.deepcopy(item_dict)


def _check_item_dict(*, item_dict, item_type):
    item_type_cap = item_type.capitalize()
    if not isinstance(item_dict, Mapping):
        raise TypeError(f"Item description has incorrect type {type(item_dict)}: a dictionary is expected")
    if "item_type" not in item_dict:
        raise ValueError(
            f"{item_type_cap} parameters can not be initialized from dictionary that does not contain item type"
        )
    dict_item_type = item_dict["item_type"]
    if dict_item_type != item_type:
        raise ValueError(
            f"{item_type_cap} parameters can not be initialized from the dictionary representing {dict_item_type}"
        )


def _check_item_args(*, passed_args, item_type):
    item_type_cap = item_type.capitalize()
    if len(passed_args) < 1:
        raise TypeError(f"{item_type_cap} name is not specified")
    if isinstance(passed_args[0], Mapping):
        _check_item_dict(item_mapping=passed_args[0], item_type=item_type)


class BPlan(BItem):
    """
    The helper class for creating and modifying a dictionary with the description of a plan item.
    The class functionality is similar to ``BItems``, but specified for operations with plans.
    The class constructor does not require or accept item type as a first argument, but instead always
    sets it to ``'plan'``. The object can be initialized from a dictionary of parameters only if
    the dictionary describes a plan item.
    """

    _class_item_type = "plan"

    def __init__(self, *args, **kwargs):
        _check_item_args(passed_args=args, item_type=self._class_item_type)
        super().__init__(self._class_item_type, *args, **kwargs)

    @BItem.item_type.setter
    def item_type(self, item_type):
        if item_type != self._class_item_type:
            raise ValueError(f"Failed to set item {self._class_item_type} type to {item_type!r}")
        BItem.item_type = item_type

    def from_dict(self, item_dict):
        """
        The method copies item parameters from the dictionary. All the existing item parameters
        are discarded. The function fails if the dictionary does not represent a plan.
        """
        _check_item_dict(item_dict=item_dict, item_type=self._class_item_type)
        self._item_dict = copy.deepcopy(dict(item_dict))


class BInst(BItem):
    """
    The helper class for creating and modifying a dictionary with the description of an instruction.
    The class functionality is similar to ``BItems``, but specified for operations with instructions.
    The class constructor does not require or accept item type as a first argument, but instead always
    sets it to ``'instruction'``. The object can be initialized from a dictionary of parameters only if
    the dictionary describes an instruction.
    """

    _class_item_type = "instruction"

    def __init__(self, *args, **kwargs):
        _check_item_args(passed_args=args, item_type=self._class_item_type)
        super().__init__(self._class_item_type, *args, **kwargs)

    @BItem.item_type.setter
    def item_type(self, item_type):
        if item_type != self._class_item_type:
            raise ValueError(f"Failed to set item {self._class_item_type} type to {item_type!r}")
        BItem.item_type = item_type

    def from_dict(self, item_dict):
        """
        The method copies item parameters from the dictionary. All the existing item parameters
        are discarded. The function fails if the dictionary does not represent a plan.
        """
        _check_item_dict(item_dict=item_dict, item_type=self._class_item_type)
        self._item_dict = copy.deepcopy(dict(item_dict))


class BFunc(BItem):
    """
    The helper class for creating and modifying a dictionary with the description of a function item.
    The class functionality is similar to ``BItems``, but specified for operations with function descriptions.
    The class constructor does not require or accept item type as a first argument, but instead always
    sets it to ``'function'``. The object can be initialized from a dictionary of parameters only if
    the dictionary describes a function item.
    """

    _class_item_type = "function"

    def __init__(self, *args, **kwargs):
        _check_item_args(passed_args=args, item_type=self._class_item_type)
        super().__init__(self._class_item_type, *args, **kwargs)

    @BItem.item_type.setter
    def item_type(self, item_type):
        if item_type != self._class_item_type:
            raise ValueError(f"Failed to set item {self._class_item_type} type to {item_type!r}")
        BItem.item_type = item_type

    def from_dict(self, item_dict):
        """
        The method copies item parameters from the dictionary. All the existing item parameters
        are discarded. The function fails if the dictionary does not represent a plan.
        """
        _check_item_dict(item_dict=item_dict, item_type=self._class_item_type)
        self._item_dict = copy.deepcopy(dict(item_dict))

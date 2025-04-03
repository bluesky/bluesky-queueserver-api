from bluesky import Msg
from bluesky_queueserver_api import WaitMonitor, BItem, BPlan, BInst
from bluesky_queueserver_api.zmq import REManagerAPI as ZMQ_REManagerAPI
from bluesky_queueserver_api.zmq.aio import REManagerAPI as ZMQ_REManagerAPI_AIO
from bluesky_queueserver_api.http import REManagerAPI as HTTP_REManagerAPI
from bluesky_queueserver_api.http.aio import REManagerAPI as HTTP_REManagerAPI_AIO
from typing import Callable, List, Iterable

from ..re_command import REMOTE_QUEUE_COMMAND

UnionREManagerAPI = (
        ZMQ_REManagerAPI | ZMQ_REManagerAPI_AIO | HTTP_REManagerAPI | HTTP_REManagerAPI_AIO
)
Item = dict | BItem | BPlan | BInst
Items = List[dict] | List[BItem] | List[BPlan] | List[BInst]


def close(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Close the RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "close", [], {"lock_key": lock_key})
    )


def user(rm: UnionREManagerAPI, name: str | None = None):
    """
    Get or set the default user name.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    name : str, optional
        The user name to set. If None, the current user name is returned.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "user", [name], {}))


def user_group(rm: UnionREManagerAPI, name: str | None = None):
    """
    Get or set the default user group name.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    name : str, optional
        The user group name to set. If None, the current user group name is returned.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "user_group", [name], {}))


def set_user_name_to_login_name(rm: UnionREManagerAPI):
    """
    Set the default user name to 'login name'.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "set_user_name_to_login_name", [], {})
    )


def status(rm: UnionREManagerAPI, reload: bool = False):
    """
    Load status of RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    reload : bool, optional
        If True, reload the status.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "status", [], {"reload": reload}))


def ping(rm: UnionREManagerAPI, reload: bool = False):
    """
    Ping the RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    reload : bool, optional
        If True, reload the status.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "ping", [], {"reload": reload}))


def config_get(rm: UnionREManagerAPI):
    """
    Returns config info for RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "config_get", [], {}))


def wait_for_idle(
        rm: UnionREManagerAPI, timeout: float = 600, monitor: WaitMonitor | None = None
):
    """
    Wait for RE Manager to return to "idle" state.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    timeout : float, optional
        Timeout in seconds.
    monitor : WaitMonitor, optional
        Monitor for waiting.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "wait_for_idle",
            [],
            {"timeout": timeout, "monitor": monitor},
        )
    )


def wait_for_idle_or_paused(
        rm: UnionREManagerAPI, timeout: float = 600, monitor: WaitMonitor | None = None
):
    """
    Wait for RE Manager to switch to idle or paused state.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    timeout : float, optional
        Timeout in seconds.
    monitor : WaitMonitor, optional
        Monitor for waiting.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "wait_for_idle_or_paused",
            [],
            {"timeout": timeout, "monitor": monitor},
        )
    )


def wait_for_idle_or_running(
        rm: UnionREManagerAPI, timeout: float = 600, monitor: WaitMonitor | None = None
):
    """
    Wait for RE Manager to switch to idle or executing_queue state.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    timeout : float, optional
        Timeout in seconds.
    monitor : WaitMonitor, optional
        Monitor for waiting.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "wait_for_idle_or_running",
            [],
            {"timeout": timeout, "monitor": monitor},
        )
    )


def wait_for_condition(
        rm: UnionREManagerAPI,
        condition: Callable,
        timeout: float = 600,
        monitor: WaitMonitor | None = None,
):
    """
    Wait for arbitrary conditions based on RE Manager status and/or user-provided data.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    condition : Callable
        Condition to wait for.
    timeout : float, optional
        Timeout in seconds.
    monitor : WaitMonitor, optional
        Monitor for waiting.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "wait_for_condition",
            [condition],
            {"timeout": timeout, "monitor": monitor},
        )
    )


def environment_open(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Open RE Worker environment.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "environment_open", [], {"lock_key": lock_key}
        )
    )


def environment_close(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Close RE Worker environment.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "environment_close", [], {"lock_key": lock_key}
        )
    )


def environment_destroy(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Destroy RE Worker environment.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "environment_destroy", [], {"lock_key": lock_key}
        )
    )


def environment_update(
        rm: UnionREManagerAPI, run_in_background: bool = False, lock_key: str | None = None
):
    """
    Update RE Worker environment cache.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    run_in_background : bool, optional
        If True, run the update in the background.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "environment_update",
            [],
            {"run_in_background": run_in_background, "lock_key": lock_key},
        )
    )


def permissions_reload(
        rm: UnionREManagerAPI,
        restore_plans_devices: bool | None = None,
        restore_permissions: bool | None = None,
        lock_key: str | None = None,
):
    """
    Generate new lists of allowed plans and devices based on current user group permissions and the lists of existing
    plans and devices.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    restore_plans_devices : bool, optional
        If True, restore plans and devices.
    restore_permissions : bool, optional
        If True, restore permissions.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "permissions_reload",
            [],
            {
                "restore_plans_devices": restore_plans_devices,
                "restore_permissions": restore_permissions,
                "lock_key": lock_key,
            },
        )
    )


def permissions_get(rm: UnionREManagerAPI):
    """
    Download the dictionary of user group permissions currently used by RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "permissions_get", [], {}))


def permissions_set(
        rm: UnionREManagerAPI,
        permissions,
        user_group_permissions: dict,
        lock_key: str | None = None,
):
    """
    Upload the dictionary of user group permissions.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    permissions : dict
        The permissions to set.
    user_group_permissions : dict
        The user group permissions to set.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "permissions_set",
            [permissions, user_group_permissions],
            {"lock_key": lock_key},
        )
    )


def plans_allowed(
        rm: UnionREManagerAPI, reload: bool = False, user_group: str | None = None
):
    """
    Returns the list (dictionary) of allowed plans.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    reload : bool, optional
        If True, reload the list.
    user_group : str, optional
        The user group to filter by.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "plans_allowed",
            [],
            {"reload": reload, "user_group": user_group},
        )
    )


def devices_allowed(
        rm: UnionREManagerAPI, reload: bool = False, user_group: str | None = None
):
    """
    Returns the list (dictionary) of allowed devices.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    reload : bool, optional
        If True, reload the list.
    user_group : str, optional
        The user group to filter by.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "devices_allowed",
            [],
            {"reload": reload, "user_group": user_group},
        )
    )


def plans_existing(rm: UnionREManagerAPI, reload: bool = False):
    """
    Returns the list (dictionary) of existing plans.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    reload : bool, optional
        If True, reload the list.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "plans_existing", [], {"reload": reload}
        )
    )


def devices_existing(rm: UnionREManagerAPI, reload: bool = False):
    """
    Returns the list (dictionary) of existing devices.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    reload : bool, optional
        If True, reload the list.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "devices_existing", [], {"reload": reload}
        )
    )


def queue_get(rm: UnionREManagerAPI, reload: bool = False):
    """
    Returns the list of items (plans and instructions) in the plan queue and currently running plan.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    reload : bool, optional
        If True, reload the list.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "queue_get", [], {"reload": reload})
    )


def queue_clear(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Remove all items from the plan queue.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "queue_clear", [], {"lock_key": lock_key}
        )
    )


def item_add(
        rm: UnionREManagerAPI,
        item: Item,
        pos: str | int | None = None,
        before_uid: str | None = None,
        after_uid: str | None = None,
        user: str | None = None,
        user_group: str | None = None,
        lock_key: str | None = None,
):
    """
    Add item to the queue.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    item : Item
        The item to add.
    pos : str or int, optional
        The position to add the item at.
    before_uid : str, optional
        The UID of the item to add before.
    after_uid : str, optional
        The UID of the item to add after.
    user : str, optional
        The user to add the item for.
    user_group : str, optional
        The user group to add the item for.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "item_add",
            [item],
            {
                "pos": pos,
                "before_uid": before_uid,
                "after_uid": after_uid,
                "user": user,
                "user_group": user_group,
                "lock_key": lock_key,
            },
        )
    )


def item_add_batch(
        rm: UnionREManagerAPI,
        items: Items,
        pos: str | int | None = None,
        before_uid: str | None = None,
        after_uid: str | None = None,
        user: str | None = None,
        user_group: str | None = None,
        lock_key: str | None = None,
):
    """
    Add a batch of items to the queue.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    items : Items
        The items to add.
    pos : str or int, optional
        The position to add the items at.
    before_uid : str, optional
        The UID of the item to add before.
    after_uid : str, optional
        The UID of the item to add after.
    user : str, optional
        The user to add the items for.
    user_group : str, optional
        The user group to add the items for.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "item_add_batch",
            [items],
            {
                "pos": pos,
                "before_uid": before_uid,
                "after_uid": after_uid,
                "user": user,
                "user_group": user_group,
                "lock_key": lock_key,
            },
        )
    )


def item_update(
        rm: UnionREManagerAPI,
        item: Item,
        replace: bool | None = None,
        user: str | None = None,
        user_group: str | None = None,
        lock_key: str | None = None,
):
    """
    Update an existing item in the queue.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    item : Item
        The item to update.
    replace : bool, optional
        If True, replace the item.
    user : str, optional
        The user to update the item for.
    user_group : str, optional
        The user group to update the item for.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "item_update",
            [item],
            {
                "replace": replace,
                "user": user,
                "user_group": user_group,
                "lock_key": lock_key,
            },
        )
    )


def item_get(
        rm: UnionREManagerAPI, pos: str | int | None = None, uid: str | None = None
):
    """
    Load an existing queue item.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    pos : str or int, optional
        The position of the item in the queue.
    uid : str, optional
        The UID of the item.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "item_get", [], {"pos": pos, "uid": uid}
        )
    )


def item_remove(
        rm: UnionREManagerAPI,
        pos: str | int | None = None,
        uid: str | None = None,
        lock_key: str | None = None,
):
    """
    Remove an item from the queue.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    pos : str or int, optional
        The position of the item in the queue.
    uid : str, optional
        The UID of the item.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "item_remove",
            [],
            {"pos": pos, "uid": uid, "lock_key": lock_key},
        )
    )


def item_remove_batch(
        rm: UnionREManagerAPI,
        uids: List[str],
        ignore_missing: bool | None = None,
        lock_key: str | None = None,
):
    """
    Remove a batch of items from the queue.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    uids : list of str
        The UIDs of the items to remove.
    ignore_missing : bool, optional
        If True, ignore missing items.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "item_remove_batch",
            [],
            {"uids": uids, "ignore_missing": ignore_missing, "lock_key": lock_key},
        )
    )


def item_move(
        rm: UnionREManagerAPI,
        pos: str | int | None = None,
        uid: str | None = None,
        pos_dest: str | int | None = None,
        before_uid: str | None = None,
        after_uid: str | None = None,
        lock_key: str | None = None,
):
    """
    Move an item to a different position in the queue.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    pos : str or int, optional
        The current position of the item in the queue.
    uid : str, optional
        The UID of the item.
    pos_dest : str or int, optional
        The destination position of the item in the queue.
    before_uid : str, optional
        The UID of the item to move before.
    after_uid : str, optional
        The UID of the item to move after.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "item_move",
            [],
            {
                "pos": pos,
                "uid": uid,
                "pos_dest": pos_dest,
                "before_uid": before_uid,
                "after_uid": after_uid,
                "lock_key": lock_key,
            },
        )
    )


def item_move_batch(
        rm: UnionREManagerAPI,
        uids: List[str],
        pos_dest: str | int | None = None,
        before_uid: str | None = None,
        after_uid: str | None = None,
        reorder: bool | None = None,
        lock_key: str | None = None,
):
    """
    Move a batch of items to a different position in the queue.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    uids : list of str
        The UIDs of the items to move.
    pos_dest : str or int, optional
        The destination position of the items in the queue.
    before_uid : str, optional
        The UID of the item to move before.
    after_uid : str, optional
        The UID of the item to move after.
    reorder : bool, optional
        If True, reorder the items.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "item_move_batch",
            [],
            {
                "uids": uids,
                "pos_dest": pos_dest,
                "before_uid": before_uid,
                "after_uid": after_uid,
                "reorder": reorder,
                "lock_key": lock_key,
            },
        )
    )


def item_execute(
        rm: UnionREManagerAPI,
        item: Item,
        user: str | None = None,
        user_group: str | None = None,
        lock_key: str | None = None,
):
    """
    Immediately execute the submitted item.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    item : Item
        The item to execute.
    user : str, optional
        The user to execute the item for.
    user_group : str, optional
        The user group to execute the item for.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "item_execute",
            [item],
            {"user": user, "user_group": user_group, "lock_key": lock_key},
        )
    )


def queue_start(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Start execution of the queue.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "queue_start", [], {"lock_key": lock_key}
        )
    )


def queue_stop(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Request RE Manager to stop execution of the queue after completion of the currently running plan.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "queue_stop", [], {"lock_key": lock_key}
        )
    )


def queue_stop_cancel(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Cancel the pending request to stop execution of the queue after the currently running plan.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "queue_stop_cancel", [], {"lock_key": lock_key}
        )
    )


def queue_mode_set(rm: UnionREManagerAPI, **kwargs):
    """
    Set parameters that define the mode of plan queue execution.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    kwargs : dict
        The parameters to set.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "queue_mode_set", [], kwargs))


def queue_autostart(rm: UnionREManagerAPI, enable: bool, lock_key: str | None = None):
    """
    Enable/disable autostart mode.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    enable : bool
        If True, enable autostart mode.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "queue_autostart",
            [enable],
            {"lock_key": lock_key},
        )
    )


def history_get(rm: UnionREManagerAPI, reload: bool = False):
    """
    Returns the list of plans in the history.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    reload : bool, optional
        If True, reload the list.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "history_get", [], {"reload": reload})
    )


def history_clear(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Remove all items from the history.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "history_clear", [], {"lock_key": lock_key}
        )
    )


def lock(
        rm: UnionREManagerAPI,
        lock_key: str | None = None,
        environment: bool | None = None,
        queue: bool | None = None,
        user: str | None = None,
        note: str | None = None,
):
    """
    Lock RE Manager with a lock key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.
    environment : bool, optional
        If True, lock the environment.
    queue : bool, optional
        If True, lock the queue.
    user : str, optional
        The user to lock for.
    note : str, optional
        A note for the lock.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "lock",
            [lock_key],
            {"environment": environment, "queue": queue, "user": user, "note": note},
        )
    )


def lock_environment(
        rm: UnionREManagerAPI,
        lock_key: str | None = None,
        note: str | None = None,
        user: str | None = None,
):
    """
    Locks the environment in RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.
    note : str, optional
        A note for the lock.
    user : str, optional
        The user to lock for.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "lock_environment",
            [lock_key],
            {"note": note, "user": user},
        )
    )


def lock_queue(
        rm: UnionREManagerAPI,
        lock_key: str | None = None,
        note: str | None = None,
        user: str | None = None,
):
    """
    Locks the queue in RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.
    note : str, optional
        A note for the lock.
    user : str, optional
        The user to lock for.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "lock_queue",
            [lock_key],
            {"note": note, "user": user},
        )
    )


def lock_all(
        rm: UnionREManagerAPI,
        lock_key: str | None = None,
        note: str | None = None,
        user: str | None = None,
):
    """
    Locks the environment and the queue in RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.
    note : str, optional
        A note for the lock.
    user : str, optional
        The user to lock for.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "lock_all",
            [lock_key],
            {"note": note, "user": user},
        )
    )


def unlock(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Unlock RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "unlock", [lock_key], {}))


def lock_info(rm: UnionREManagerAPI, lock_key: str | None = None, reload: bool = False):
    """
    Returns status information of the current lock.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.
    reload : bool, optional
        If True, reload the information.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "lock_info", [lock_key], {"reload": reload}
        )
    )


def lock_key(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Get/set current lock key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to set.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "lock_key", [lock_key], {}))


def enable_locked_api(rm: UnionREManagerAPI, enable: bool):
    """
    Enable/disable access to locked API.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    enable : bool
        If True, enable access to locked API.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "enable_locked_api", [enable], {}))


def get_default_lock_key(rm: UnionREManagerAPI, new_key: bool = False):
    """
    Returns the default lock key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    new_key : bool, optional
        If True, generate a new key.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "get_default_lock_key", [new_key], {})
    )


def set_default_lock_key(rm: UnionREManagerAPI, lock_key: str):
    """
    Set the default lock key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str
        The lock key to set.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "set_default_lock_key", [lock_key], {})
    )


def default_lock_key_path(rm: UnionREManagerAPI, path: str):
    """
    Get/set path of the file with the default lock key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    path : str
        The path to set.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "default_lock_key_path", [path], {})
    )


def script_upload(
        rm: UnionREManagerAPI,
        script: str,
        update_lists: bool = True,
        update_re: bool = False,
        run_in_background: bool = False,
        lock_key: str | None = None,
):
    """
    Upload a script to the RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    script : str
        The script to upload.
    update_lists : bool, optional
        If True, update the lists of allowed plans and devices.
    update_re : bool, optional
        If True, update the RE Manager.
    run_in_background : bool, optional
        If True, run the upload in the background.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "script_upload",
            [script],
            {
                "update_lists": update_lists,
                "update_re": update_re,
                "run_in_background": run_in_background,
                "lock_key": lock_key,
            },
        )
    )


def function_execute(
        rm: UnionREManagerAPI,
        item: Item,
        run_in_background: bool = False,
        user: str | None = None,
        user_group: str | None = None,
        lock_key: str | None = None,
):
    """
    Execute a function on the RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    item : Item
        The function to execute.
    run_in_background : bool, optional
        If True, run the function in the background.
    user : str, optional
        The user to execute the function for.
    user_group : str, optional
        The user group to execute the function for.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "function_execute",
            [item],
            {
                "run_in_background": run_in_background,
                "user": user,
                "user_group": user_group,
                "lock_key": lock_key,
            },
        )
    )


def task_status(rm: UnionREManagerAPI, task_uid: str | Iterable[str]):
    """
    Get the status of a task.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    task_uid : str or iterable of str
        The UID(s) of the task(s).

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "task_status", [task_uid], {}))


def task_result(rm: UnionREManagerAPI, task_uid: str):
    """
    Get the result of a task.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    task_uid : str
        The UID of the task.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "task_result", [task_uid], {}))


def wait_for_completed_task(
        rm: UnionREManagerAPI,
        task_uid: str | Iterable[str],
        timeout: float = 600,
        monitor: WaitMonitor | None = None,
        treat_not_found_as_completed: bool = True,
):
    """
    Wait for a task to complete.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    task_uid : str or iterable of str
        The UID(s) of the task(s).
    timeout : float, optional
        Timeout in seconds.
    monitor : WaitMonitor, optional
        Monitor for waiting.
    treat_not_found_as_completed : bool, optional
        If True, treat not found tasks as completed.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "wait_for_completed_task",
            [task_uid],
            {
                "timeout": timeout,
                "monitor": monitor,
                "treat_not_found_as_completed": treat_not_found_as_completed,
            },
        )
    )


def re_runs(rm: UnionREManagerAPI, option: str | None = None, reload: bool = False):
    """
    Get the list of completed runs.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    option : str, optional
        The option to filter the runs.
    reload : bool, optional
        If True, reload the list.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "re_runs", [option], {"reload": reload}
        )
    )


def re_pause(
        rm: UnionREManagerAPI, option: str | None = None, lock_key: str | None = None
):
    """
    Pause the currently running plan.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    option : str, optional
        The option to pause the plan.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "re_pause", [option], {"lock_key": lock_key}
        )
    )


def re_resume(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Resume the currently paused plan.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "re_resume", [], {"lock_key": lock_key}
        )
    )


def re_stop(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Stop the currently running plan.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "re_stop", [], {"lock_key": lock_key})
    )


def re_abort(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Abort the currently running plan.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "re_abort", [], {"lock_key": lock_key})
    )


def re_halt(rm: UnionREManagerAPI, lock_key: str | None = None):
    """
    Halt the currently running plan.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(REMOTE_QUEUE_COMMAND, rm, "re_halt", [], {"lock_key": lock_key})
    )


def kernel_interrupt(
        rm: UnionREManagerAPI,
        interrupt_task: bool | None = None,
        interrupt_plan: bool | None = None,
        lock_key: str | None = None,
):
    """
    Interrupt the IPython kernel.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    interrupt_task : bool, optional
        If True, interrupt the task.
    interrupt_plan : bool, optional
        If True, interrupt the plan.
    lock_key : str, optional
        The lock key to use for the operation.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "kernel_interrupt",
            [],
            {
                "interrupt_task": interrupt_task,
                "interrupt_plan": interrupt_plan,
                "lock_key": lock_key,
            },
        )
    )


def auth_method(rm: UnionREManagerAPI):
    """
    Get the authorization method.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "auth_method", [], {}))


def auth_key(rm: UnionREManagerAPI):
    """
    Get the authorization key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "auth_key", [], {}))


def set_authorization_key(
        rm: UnionREManagerAPI,
        api_key: str | None = None,
        token: str | None = None,
        refresh_token: str | None = None,
):
    """
    Set the authorization key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    api_key : str, optional
        The API key to set.
    token : str, optional
        The token to set.
    refresh_token : str, optional
        The refresh token to set.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "set_authorization_key",
            [],
            {"api_key": api_key, "token": token, "refresh_token": refresh_token},
        )
    )


def login(
        rm: UnionREManagerAPI,
        username: str | None = None,
        password: str | None = None,
        provider: str | None = None,
):
    """
    Log in to the RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    username : str, optional
        The username to log in with.
    password : str, optional
        The password to log in with.
    provider : str, optional
        The provider to log in with.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "login",
            [username],
            {"password": password, "provider": provider},
        )
    )


def session_refresh(rm: UnionREManagerAPI, refresh_token: str | None = None):
    """
    Refresh the session.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    refresh_token : str, optional
        The refresh token to use.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "session_refresh",
            [],
            {"refresh_token": refresh_token},
        )
    )


def session_revoke(
        rm: UnionREManagerAPI,
        session_uid: str,
        token: str | None = None,
        api_key: str | None = None,
):
    """
    Revoke a session.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    session_uid : str
        The UID of the session to revoke.
    token : str, optional
        The token to use.
    api_key : str, optional
        The API key to use.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "session_revoke",
            [session_uid],
            {"token": token, "api_key": api_key},
        )
    )


def apikey_new(
        rm: UnionREManagerAPI,
        expired_in: int,
        scopes: List[str] | None = None,
        note: str | None = None,
        principal_uid: str | None = None,
):
    """
    Generate a new API key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    expired_in : int
        The expiration time of the API key in seconds.
    scopes : list of str, optional
        The scopes for the API key.
    note : str, optional
        A note for the API key.
    principal_uid : str, optional
        The UID of the principal.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "apikey_new",
            [],
            {
                "expired_in": expired_in,
                "scopes": scopes,
                "note": note,
                "principal_uid": principal_uid,
            },
        )
    )


def apikey_info(rm: UnionREManagerAPI, api_key: str | None = None):
    """
    Get information about an API key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    api_key : str, optional
        The API key to get information about.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "apikey_info", [], {"api_key": api_key}
        )
    )


def apikey_delete(
        rm: UnionREManagerAPI,
        first_eight: str,
        token: str | None = None,
        api_key: str | None = None,
):
    """
    Delete an API key.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    first_eight : str
        The first eight characters of the API key to delete.
    token : str, optional
        The token to use.
    api_key : str, optional
        The API key to use.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "apikey_delete",
            [first_eight],
            {"token": token, "api_key": api_key},
        )
    )


def whoami(rm: UnionREManagerAPI, token: str | None = None, api_key: str | None = None):
    """
    Get information about the current user.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    token : str, optional
        The token to use.
    api_key : str, optional
        The API key to use.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND, rm, "whoami", [], {"token": token, "api_key": api_key}
        )
    )


def principal_info(rm: UnionREManagerAPI, principal_uid: str | None = None):
    """
    Get information about a principal.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    principal_uid : str, optional
        The UID of the principal.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "principal_info",
            [],
            {"principal_uid": principal_uid},
        )
    )


def api_scopes(
        rm: UnionREManagerAPI, token: str | None = None, api_key: str | None = None
):
    """
    Get the API scopes.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    token : str, optional
        The token to use.
    api_key : str, optional
        The API key to use.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (
        yield Msg(
            REMOTE_QUEUE_COMMAND,
            rm,
            "api_scopes",
            [],
            {"token": token, "api_key": api_key},
        )
    )


def logout(rm: UnionREManagerAPI):
    """
    Log out from the RE Manager.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm, "logout", [], {}))


def console_monitor_enabled(rm: UnionREManagerAPI):
    """
    Enable/disable console monitor.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    enabled : bool
        If True, enable console monitor.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm.console_monitor, "enabled", [], {}))


def console_monitor_enable(rm: UnionREManagerAPI):
    """
    Enable console monitor.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm.console_monitor, "enable", [], {}))


def console_monitor_disable(rm: UnionREManagerAPI):
    """
    Disable console monitor.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm.console_monitor, "disable", [], {}))


def console_monitor_disable_wait(rm: UnionREManagerAPI, timeout: float = 2):
    """
    Disable console monitor and wait for completion.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    timeout : float, optional
        Timeout in seconds.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm.console_monitor, "disable_wait", [], {"timeout": timeout}))


def console_monitor_clear(rm: UnionREManagerAPI):
    """
    Clear console monitor.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm.console_monitor, "clear", [], {}))


def console_monitor_next_msg(rm: UnionREManagerAPI, timeout: float | None = None):
    """
    Get the next message from the console monitor.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    timeout : float, optional
        Timeout in seconds.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm.console_monitor, "next_msg", [], {"timeout": timeout}))


def console_monitor_text_max_lines(rm: UnionREManagerAPI, max_lines: int | None = None):
    """
    Get/set the maximum size of the text buffer. The new buffer size is applied to the existing buffer,
    removing extra messages if necessary.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    max_lines : int
        The maximum number of lines.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm.console_monitor, "text_max_lines", [max_lines], {}))


def console_monitor_text_uid(rm: UnionREManagerAPI):
    """
    Get the UID of the text buffer.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm.console_monitor, "text_uid", [], {}))


def console_monitor_text(rm: UnionREManagerAPI, nlines: int | None = None):
    """
    Get the text buffer.

    https://blueskyproject.io/bluesky-queueserver-api/api-reference.html

    Parameters
    ----------
    rm : UnionREManagerAPI
        The RE Manager API instance.
    nlines : int, optional
        The number of lines to get.

    Returns
    -------
    generator
        A generator that yields a Msg object.
    """
    return (yield Msg(REMOTE_QUEUE_COMMAND, rm.console_monitor, "text", [nlines], {}))







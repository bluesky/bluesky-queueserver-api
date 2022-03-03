=============
API Reference
=============

.. currentmodule:: bluesky_queueserver_api

Generation of Queue Items
-------------------------

Generic Queue Item
******************

.. autosummary::
   :nosignatures:
   :toctree: generated

    BItem
    BItem.to_dict
    BItem.from_dict
    BItem.item_type
    BItem.name
    BItem.args
    BItem.kwargs
    BItem.meta
    BItem.item_uid
    BItem.dict_ref
    BItem.recognized_item_types

Type-Specific Queue Items
*************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    BPlan
    BInst
    BFunc

Miscellaneous API
-----------------

.. autosummary::
   :nosignatures:
   :toctree: generated

    WaitMonitor
    WaitMonitor.cancel
    WaitMonitor.is_cancelled
    WaitMonitor.time_start
    WaitMonitor.time_elapsed
    WaitMonitor.timeout
    WaitMonitor.set_timeout
    WaitMonitor.add_cancel_callback

Synchronous Communication with 0MQ Server
-----------------------------------------

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI
    zmq.REManagerAPI.close

Low-Level API
*************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.send_request

API for controlling RE Manager
******************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.status
    zmq.REManagerAPI.ping
    zmq.REManagerAPI.wait_for_idle
    zmq.REManagerAPI.wait_for_idle_or_paused

API for controlling RE Environment
**********************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.environment_open
    zmq.REManagerAPI.environment_close
    zmq.REManagerAPI.environment_destroy

API for Monitoring Available Resources
**************************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.permissions_reload
    zmq.REManagerAPI.permissions_get
    zmq.REManagerAPI.permissions_set
    zmq.REManagerAPI.plans_allowed
    zmq.REManagerAPI.devices_allowed
    zmq.REManagerAPI.plans_existing
    zmq.REManagerAPI.devices_existing

API for management of RE Queue
******************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.queue_get
    zmq.REManagerAPI.queue_clear
    zmq.REManagerAPI.item_add
    zmq.REManagerAPI.item_add_batch
    zmq.REManagerAPI.item_update
    zmq.REManagerAPI.item_get
    zmq.REManagerAPI.item_remove
    zmq.REManagerAPI.item_remove_batch
    zmq.REManagerAPI.item_move
    zmq.REManagerAPI.item_move_batch
    zmq.REManagerAPI.item_execute
    zmq.REManagerAPI.queue_start
    zmq.REManagerAPI.queue_stop
    zmq.REManagerAPI.queue_stop_cancel
    zmq.REManagerAPI.queue_mode_set

API for Controlling RE History
******************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.history_get
    zmq.REManagerAPI.history_clear

API for Executing Tasks
***********************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.script_upload
    zmq.REManagerAPI.function_execute
    zmq.REManagerAPI.task_status
    zmq.REManagerAPI.task_result

API for controlling Run Engine
******************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.re_runs
    zmq.REManagerAPI.re_pause
    zmq.REManagerAPI.re_resume
    zmq.REManagerAPI.re_stop
    zmq.REManagerAPI.re_abort
    zmq.REManagerAPI.re_halt

Asynchronous Communication with 0MQ Server
------------------------------------------

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.aio.REManagerAPI

Synchronous Communication with HTTP Server
------------------------------------------

.. autosummary::
   :nosignatures:
   :toctree: generated

    http.REManagerAPI

ASynchronous Communication with HTTP Server
-------------------------------------------

.. autosummary::
   :nosignatures:
   :toctree: generated

    http.aio.REManagerAPI

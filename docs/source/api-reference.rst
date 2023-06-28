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

Configuration of REManagerAPI
*****************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.user
    zmq.REManagerAPI.user_group
    zmq.REManagerAPI.set_user_name_to_login_name

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
    zmq.REManagerAPI.config_get
    zmq.REManagerAPI.wait_for_idle
    zmq.REManagerAPI.wait_for_idle_or_paused
    zmq.REManagerAPI.wait_for_idle_or_running
    zmq.REManagerAPI.wait_for_condition

API for controlling RE Environment
**********************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.environment_open
    zmq.REManagerAPI.environment_close
    zmq.REManagerAPI.environment_destroy
    zmq.REManagerAPI.environment_update

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
    zmq.REManagerAPI.queue_autostart

API for Controlling RE History
******************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.history_get
    zmq.REManagerAPI.history_clear

API for Locking RE Manager
**************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.lock
    zmq.REManagerAPI.lock_environment
    zmq.REManagerAPI.lock_queue
    zmq.REManagerAPI.lock_all
    zmq.REManagerAPI.unlock
    zmq.REManagerAPI.lock_info
    zmq.REManagerAPI.lock_key
    zmq.REManagerAPI.enable_locked_api
    zmq.REManagerAPI.get_default_lock_key
    zmq.REManagerAPI.set_default_lock_key
    zmq.REManagerAPI.default_lock_key_path


API for Executing Tasks
***********************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.script_upload
    zmq.REManagerAPI.function_execute
    zmq.REManagerAPI.task_status
    zmq.REManagerAPI.task_result
    zmq.REManagerAPI.wait_for_completed_task

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

API for controlling IPython kernel
**********************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.kernel_interrupt

API for monitoring console output of RE manager
***********************************************

Each instance of ``REManagerAPI`` holds a reference to a Console Monitor. The reference
is accessible using the ``console_monitor`` property. The Console Monitor is initialized as
part of ``REManagerAPI`` instantiation and ready for use.

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.console_monitor

The package implements multiple console monitors (synchronous/asynchronous monitors for 0MQ and
HTTP communication), which expose identical API. The class for monitoring console output using
0MQ for synchronous applications:

.. autosummary::
   :nosignatures:
   :toctree: generated

    console_monitor.ConsoleMonitor_ZMQ_Threads
    console_monitor.ConsoleMonitor_ZMQ_Threads.enabled
    console_monitor.ConsoleMonitor_ZMQ_Threads.enable
    console_monitor.ConsoleMonitor_ZMQ_Threads.disable
    console_monitor.ConsoleMonitor_ZMQ_Threads.disable_wait
    console_monitor.ConsoleMonitor_ZMQ_Threads.clear
    console_monitor.ConsoleMonitor_ZMQ_Threads.next_msg
    console_monitor.ConsoleMonitor_ZMQ_Threads.text_max_lines
    console_monitor.ConsoleMonitor_ZMQ_Threads.text_uid
    console_monitor.ConsoleMonitor_ZMQ_Threads.text

Other console monitor classes support identical API:

.. autosummary::
   :nosignatures:
   :toctree: generated

    console_monitor.ConsoleMonitor_ZMQ_Async
    console_monitor.ConsoleMonitor_HTTP_Threads
    console_monitor.ConsoleMonitor_HTTP_Async

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

API for authentication and authorization (HTTP)
***********************************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    http.REManagerAPI.auth_method
    http.REManagerAPI.auth_key
    http.REManagerAPI.set_authorization_key
    http.REManagerAPI.login
    http.REManagerAPI.session_refresh
    http.REManagerAPI.session_revoke
    http.REManagerAPI.apikey_new
    http.REManagerAPI.apikey_info
    http.REManagerAPI.apikey_delete
    http.REManagerAPI.whoami
    http.REManagerAPI.principal_info
    http.REManagerAPI.api_scopes
    http.REManagerAPI.logout

ASynchronous Communication with HTTP Server
-------------------------------------------

.. autosummary::
   :nosignatures:
   :toctree: generated

    http.aio.REManagerAPI

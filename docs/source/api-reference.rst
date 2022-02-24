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
    zmq.REManagerAPI.wait_for_idle


API for controlling RE Environment
**********************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.environment_open
    zmq.REManagerAPI.environment_close
    zmq.REManagerAPI.environment_destroy


API for management of RE Queue
******************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.item_add
    zmq.REManagerAPI.item_get
    zmq.REManagerAPI.queue_start


API for controlling RE History
******************************

API for controlling Run Engine
******************************


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

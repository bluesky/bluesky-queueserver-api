=============
API Reference
=============

.. currentmodule:: bluesky_queueserver_api

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

API for management of RE Queue
******************************

.. autosummary::
   :nosignatures:
   :toctree: generated

    zmq.REManagerAPI.add_item


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

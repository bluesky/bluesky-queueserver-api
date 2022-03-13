===============
Release History
===============

v0.0.3 (2022-03-08)
===================

Fixed
-----

- Proper handling of exceptions by ``wait_..`` API (such as ``wait_for_idle``). All exceptions
  are handled internally by the functions. If server is not accessible (requests timed out),
  then the API also times out (``REManagerAPI.WaitTimeoutError`` exception is raised).

Changed
-------

- Renamed parameters of ``permissions_reload`` API: ``reload_permissions`` is renamed to
  ``restore_permissions``, ``reload_plans_devices`` is renamed to ``restore_plans_devices``.

v0.0.2 (2022-03-03)
===================

Added
-----

* Implementation of the full set of basic API.


v0.0.1 (2022-02-24)
===================

Added
-----

* Initial release of the API.

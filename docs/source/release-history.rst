===============
Release History
===============

v0.0.11 (2024-07-25)
====================

Maintenance release. There are no API changes.


v0.0.10 (2023-06-28)
====================

Added
-----

- New API: ``config_get``, ``queue_autostart``, ``environment_update``, ``kernel_interrupt``,
  ``wait_for_condition``, ``wait_for_idle_or_running``.

- ``queue_mode_set`` API can now set ``ignore_failures`` mode.


v0.0.9 (2022-10-02)
===================

Added
-----

- New API (HTTP communication): ``login``, ``session_refresh``, ``session_revoke``, ``apikey_new``,
  ``apikey_info``, ``apikey_delete``, ``whoami``, ``principal_info``, ``api_scopes``,
  ``logout``.

- Added automatic session refresh functionality to ``send_request`` API.

- New parameters of constructor of HTTP version of ``REManagerAPI``: ``http_auth_provider``
  and ``timeout_login``.

- New parameter of ``send_request`` API: ``auto_refresh_session``. The parameter controls
  whether the function attempts to refresh expired sessions (get new access token based on
  valid refresh token). By default it is *True*, which works for most cases. In some cases
  (e.g. in implementation of authentication/authorization API) automatic refresh should be disabled.

Changed
-------

- Renamed the exception ``RequestError`` to ``HTTPRequestError``.

- Renamed the exception ``ClientError`` to ``HTTPClientError``.

- The new exception ``HTTPServerError`` is raised if code 500 is returned by the server
  (instead of ``ClientError``).

- Default user group is renamed from 'admin' to 'primary'. Rename the user group in
  'user_group_permissions.yaml' if the workflow depends on the default user group name.


Removed
-------

- Removed the parameter ``api_prefix`` from the constructor of HTTP version of ``REManagerAPI``.
  The prefix should be added directly to ``http_server_uri``.


v0.0.8 (2022-08-11)
===================

Added
-----

- New API: ``REManagerAPI.wait_for_completed_task()``.

Changed
-------

- ``REManagerAPI.task_status()`` now accepts any iterable with task UIDs, not only a list.
  Iterables are converted to lists internally.


v0.0.7 (2022-07-30)
===================

Added
-----

- Support for ``update_lists`` parameter of ``script_upload`` API.

- Support for ``lock``, ``lock_info`` and ``unlock`` API of RE Manager. New methods for REManagerAPI:
  ``lock()``, ``lock_environment()``, ``lock_queue()``, ``lock_all()``, ``lock_info()``, ``unlock()``.
  Additional methods and properties: ``default_lock_key_path``, ``get_default_lock_key()``,
  ``set_default_lock_key()``, ``lock_key``, ``enable_locked_api``.


v0.0.6 (2022-06-30)
===================

Added
-----

- Read/write properties ``REManagerAPI.user`` and ``REManagerAPI.user_group`` for access to default user name
  and user group.

- New configuration API: ``REManagerAPI.set_user_name_to_login_name()``. The API sets the default user name to
  login name of the workstation user.

- Implemented support for environment variables for passing parameters to ``REManagerAPI`` constructor.
  The respective constructor parameters override the values set by environment variables. The following
  environment variables are supported:

  - ``QSERVER_ZMQ_CONTROL_ADDRESS`` may be used instead of ``zmq_control_addr`` (0MQ);
  - ``QSERVER_ZMQ_INFO_ADDRESS`` may be used instead of ``zmq_info_addr`` (0MQ);
  - ``QSERVER_ZMQ_PUBLIC_KEY`` may be used instead of ``zmq_public_key`` (0MQ);
  - ``QSERVER_HTTP_SERVER_URI`` may be used instead of ``http_server_uri`` (HTTP).

- A parameter ``nlines`` was added to ``REManagerAPI.console_monitor.text()`` API.
  The parameter specifies the maximum number of lines returned by the function.

- New API ``REManagerAPI.set_authorization_key()`` that allows to set authorization keys for REST API
  (only in HTTP version). Only API keys are currently supported. Tokens and refresh tokens will be supported in the future.

- New parameter in the constructor of ``REManagerAPI`` (HTTP version): ``api_prefix``.


Changed
-------

- The API functions that send user name and user group as part of request to the server are now accepting ``user``
  and ``user_group`` parameters that override current default values. The API include ``plans_allowed``,
  ``devices_allowed``, ``item_add``, ``item_add_batch``, ``item_update``, ``item_execute``, ``function_execute``.
  HTTP version of the API is not sending user name and user group to the server and values of
  ``user`` and ``user_group`` parameters are ignored.

- Renamed some parameters of ``REManagerAPI`` constructors. The new names will be consistently used in Queue Server
  and related tools. The renamed parameters include ``zmq_control_addr`` (the address of control socket of RE Manager),
  ``zmq_info_addr`` (the address of information PUB socket of RE Manager, currently used only for console output),
  ``zmq_public_key`` (public key for encrypted communication with RE Manager), ``http_server_uri`` - URI of Bluesky HTTP server.

- ``REManagerAPI.console_monitor.text_updated`` property was replaced with ``...text_uid`` property as more appropriate
  for monitoring of the state of the text buffer.


v0.0.5 (2022-04-09)
===================

Added
-----

- Support for text buffer in ``RE.console_monitor``.


v0.0.4 (2022-04-05)
===================

Added
-----

- API for monitoring of console output: ``REManagerAPI.console_monitor``

Changed
-------

- Updated API docstrings.


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

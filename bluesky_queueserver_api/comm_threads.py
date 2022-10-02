import httpx

from .comm_base import ReManagerAPI_ZMQ_Base, ReManagerAPI_HTTP_Base
from bluesky_queueserver import ZMQCommSendThreads

from .api_docstrings import _doc_send_request, _doc_close, _doc_api_login, _doc_api_session_refresh
from .console_monitor import ConsoleMonitor_ZMQ_Threads, ConsoleMonitor_HTTP_Threads


class ReManagerComm_ZMQ_Threads(ReManagerAPI_ZMQ_Base):
    def _init_console_monitor(self):
        self._console_monitor = ConsoleMonitor_ZMQ_Threads(
            zmq_info_addr=self._zmq_info_addr,
            poll_timeout=self._console_monitor_poll_timeout,
            max_msgs=self._console_monitor_max_msgs,
            max_lines=self._console_monitor_max_lines,
        )

    def _create_client(
        self,
        *,
        zmq_control_addr,
        timeout_recv,
        timeout_send,
        zmq_public_key,
    ):
        return ZMQCommSendThreads(
            zmq_server_address=zmq_control_addr,
            timeout_recv=int(timeout_recv * 1000),  # Convert to ms
            timeout_send=int(timeout_send * 1000),  # Convert to ms
            raise_exceptions=True,
            server_public_key=zmq_public_key,
        )

    def send_request(self, *, method, params=None):
        try:
            response = self._client.send_message(method=method, params=params)
        except Exception:
            self._process_comm_exception(method=method, params=params)
        self._check_response(request={"method": method, "params": params}, response=response)

        return response

    def close(self):
        self._is_closing = True
        self._console_monitor.disable_wait(timeout=self._console_monitor_poll_timeout * 10)
        self._client.close()

    def __del__(self):
        self._is_closing = True


class ReManagerComm_HTTP_Threads(ReManagerAPI_HTTP_Base):
    def _init_console_monitor(self):
        self._console_monitor = ConsoleMonitor_HTTP_Threads(
            parent=self,
            poll_period=self._console_monitor_poll_period,
            max_msgs=self._console_monitor_max_msgs,
            max_lines=self._console_monitor_max_lines,
        )

    def _create_client(self, http_server_uri, timeout):
        timeout = self._adjust_timeout(timeout)
        return httpx.Client(base_url=http_server_uri, timeout=timeout)

    def _simple_request(self, *, method, params=None, url_params=None, headers=None, data=None, timeout=None):
        """
        The code that formats and sends a simple request.
        """
        try:
            client_response = None
            request_method, endpoint, params = self._prepare_request(method=method, params=params)
            headers = headers or self._prepare_headers()
            kwargs = {"json": params}
            if url_params:
                kwargs.update({"params": url_params})
            if headers:
                kwargs.update({"headers": headers})
            if data:
                kwargs.update({"data": data})
            if timeout is not None:
                kwargs.update({"timeout": self._adjust_timeout(timeout)})
            client_response = self._client.request(request_method, endpoint, **kwargs)
            response = self._process_response(client_response=client_response)

        except Exception:
            response = self._process_comm_exception(method=method, params=params, client_response=client_response)

        self._check_response(request={"method": method, "params": params}, response=response)

        return response

    def send_request(
        self,
        *,
        method,
        params=None,
        url_params=None,
        headers=None,
        data=None,
        timeout=None,
        auto_refresh_session=True,
    ):
        # Docstring is maintained separately
        refresh = False
        request_params = {
            "method": method,
            "params": params,
            "url_params": url_params,
            "headers": headers,
            "data": data,
            "timeout": timeout,
        }
        try:
            response = self._simple_request(**request_params)
        except self.HTTPClientError as ex:
            # The session is supposed to be automatically refreshed only if the expired token is passed
            #   to the server. Otherwise the request is expected to fail.
            if (
                auto_refresh_session
                and ("401: Access token has expired" in str(ex))
                and (self.auth_method == self.AuthorizationMethods.TOKEN)
                and (self.auth_key[1] is not None)
            ):
                refresh = True
            else:
                raise

        if refresh:
            try:
                self.session_refresh()
            except Exception as ex:
                print(f"Failed to refresh session: {ex}")

            # Try calling the API with the new token (or the old one if refresh failed).
            response = self._simple_request(**request_params)

        return response

    def login(self, username=None, *, password=None, provider=None):
        # Docstring is maintained separately
        endpoint, data = self._prepare_login(username=username, password=password, provider=provider)
        response = self.send_request(
            method=("POST", endpoint), data=data, timeout=self._timeout_login, auto_refresh_session=False
        )
        response = self._process_login_response(response=response)
        return response

    def session_refresh(self, *, refresh_token=None):
        # Docstring is maintained separately
        refresh_token = self._prepare_refresh_session(refresh_token=refresh_token)
        response = self.send_request(
            method="session_refresh", params={"refresh_token": refresh_token}, auto_refresh_session=False
        )
        response = self._process_login_response(response=response)
        return response

    def session_revoke(self, *, session_uid, token=None, api_key=None):
        """
        Revoke session for an authorized user. If the session is revoked, the respective refresh
        token can no longer be used to refresh session. Access tokens and API keys will continue
        working. By default the API request is authorized using the default authorization key
        (set using ``set_authorization_key()`` or as a result of login). A token or an API key
        passed as a parameter override the default authorization key, which allows to revoke
        sessions for different users without changing the default authorization key (without
        logging out).

        Example
        -------

        Log into the server, find UID of a session and revoke the session.

            RM.login("bob", password="bob_password")
            RM.whoami()

            # {'uuid': '352cae89-7e94-45be-a405-c39099ebe515',
            #  'type': 'user',
            #  'identities': [
            #     {'id': 'bob',
            #       'provider': 'toy',
            #       'latest_login': '2022-10-02T02:47:57'}],
            #       'api_keys': [],
            #       'sessions': [{'uuid': 'e544d4b6-4750-43c3-8ba0-b7e9aedd2045',
            #                     'expiration_time': '2023-10-01T19:28:15',
            #                     'revoked': False},
            #                    {'uuid': '66ee49c1-32b4-4778-8502-205e35151736',
            #                     'expiration_time': '2023-10-01T19:30:03',
            #                     'revoked': False},
            #       .....................................................
            #                    {'uuid': 'c41d2f01-607e-49c0-9b3e-a93c383330c0',
            #                     'expiration_time': '2023-10-02T02:47:57',
            #                     'revoked': False}],
            #       'latest_activity': '2022-10-02T02:47:57',
            #       'roles': [],
            #       'scopes': [],
            #       'api_key_scopes': None}

            # Let's revoke session "e544d4b6-4750-43c3-8ba0-b7e9aedd2045"
            RM.session_revoke(session_uid="e544d4b6-4750-43c3-8ba0-b7e9aedd2045")

            result = RM.whoami()

            # NOTE: the session is now labeled as revoked ("revoked": True)
            # {'uuid': '352cae89-7e94-45be-a405-c39099ebe515',
            #  'type': 'user',
            #  'identities': [
            #     {'id': 'bob',
            #       'provider': 'toy',
            #       'latest_login': '2022-10-02T02:47:57'}],
            #       'api_keys': [],
            #       'sessions': [{'uuid': 'e544d4b6-4750-43c3-8ba0-b7e9aedd2045',
            #                     'expiration_time': '2023-10-01T19:28:15',
            #                     'revoked': True},
            #                    {'uuid': '66ee49c1-32b4-4778-8502-205e35151736',
            #                     'expiration_time': '2023-10-01T19:30:03',
            #                     'revoked': False},
            #       .....................................................
            #                    {'uuid': 'c41d2f01-607e-49c0-9b3e-a93c383330c0',
            #                     'expiration_time': '2023-10-02T02:47:57',
            #                     'revoked': False}],
            #       'latest_activity': '2022-10-02T02:47:57',
            #       'roles': [],
            #       'scopes': [],
            #       'api_key_scopes': None}

        Parameters
        ----------
        session_uid: str
            Full session UID. Session UID may be obtained from results returned by
            ``REManagerAPI.whoami()`` or ``REManagerAPI.principal_info()``.
        token, api_key: str or None, optional
            Access token or an API key. The parameters are mutually exclusive: the API fails
            if both parameters are not *None*. A token or an API key overrides the default
            security key. Default: *None*.

        Returns
        -------
        dict
            Returns the dictionary ``{'success': True, 'msg': ''}`` if success.

        Raises
        ------
        RequestParameterError
            Incorrect or insufficient parameters in the API call.
        HTTPRequestError, HTTPClientError, HTTPServerError
            Error while sending and processing HTTP request.

        """
        # Docstring is maintained separately
        method, headers = self._prepare_session_revoke(session_uid=session_uid, token=token, api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = self.send_request(method=method, **kwargs)
        return response

    def apikey_new(self, *, expires_in, scopes=None, note=None, principal_uid=None):
        """
        Generate a new API key for authorized user. The API request is authorized using the
        default security key (set using ``set_authorization_key()`` or as a result of login).

        Users with administrative privileges can generate API keys for other users based on
        principal UID. Principal UID may be found using ``REManagerAPI.whoami()`` or
        ``REManagerAPI.principal_info()``.

        Example
        -------
        Log into the server and create an API key, which inherits the scopes from principal::

            RM.login("bob", password="bob_password")
            result = RM.apikey_new(expires_in=900)

            # {'first_eight': '66ccb3ca',
            #  'expiration_time': '2022-10-02T03:29:20',
            #  'note': None,
            #  'scopes': ['inherit'],
            #  'latest_activity': None,
            #  'secret': '66ccb3ca33ea091ab297331ba2589bdcf7ea9f5f168dbfd90c156652d1cedd9533c1bc59'}

        Parameters
        ----------
        expires_in: int
            Duration of API lifetime in seconds. Lifetime must be positive non-zero integer.
        scopes: list(str) or None, optional
            Optional list of scopes, such as ``["read:status", "read:queue", "user:apikeys"]``.
            If the value is ``None`` (default), then the new API inherits the allowed scopes
            of the principal (if authorized with token) or the original API key (if authorized
            with API key). Default: *None*.
        note: str or None, optional
            Optional note. Default: *None*.
        principal_uid: str or None, optional
            Principal UID of a user. Including principal UID allows to create API keys
            for any user registered in the database (user who logged into the server at least
            once). This operation requires administrative privileges. The API fails if
            ``principal_uid`` is not *None* and authorization is performed with security key
            that does not have administrative privileges. Default: *None*.

        Returns
        -------
        dict
            The API key is returned as ``'secret'`` key of the dictionary.

        Raises
        ------
        RequestParameterError
            Incorrect or insufficient parameters in the API call.
        HTTPRequestError, HTTPClientError, HTTPServerError
            Error while sending and processing HTTP request.
        """
        # Docstring is maintained separately
        method, request_params = self._prepare_apikey_new(
            expires_in=expires_in, scopes=scopes, note=note, principal_uid=principal_uid
        )
        response = self.send_request(method=method, params=request_params)
        return response

    def apikey_info(self, *, api_key=None):
        """
        Get information about an API key. The API returning information about the API
        key used to authorize the request. The request fails if a token is used for
        authorization. If the parameter ``api_key`` is *None*, then the default
        security key (set by ``REManagerAPI.set_authorization_key()`` and must be
        an API key, not a token) is used. The API key passed with the parameter ``api_key``
        override the default security key (the default is ignored). This allows to
        obtain information on any API key without logging out or changing
        the default security key.

        Parameters
        ----------
        api_key: str or None, optional
            API key of interest. The parameter is used for authorization of the request
            instead of the default security key, which is ignored. Default: ``None``.

        Raises
        ------
        RequestParameterError
            Incorrect or insufficient parameters in the API call.
        HTTPRequestError, HTTPClientError, HTTPServerError
            Error while sending and processing HTTP request.
        """
        # Docstring is maintained separately
        headers = self._prepare_apikey_info(api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = self.send_request(method="apikey_info", **kwargs)
        return response

    def apikey_delete(self, *, first_eight, token=None, api_key=None):
        # Docstring is maintained separately
        url_params, headers = self._prepare_apikey_delete(first_eight=first_eight, token=token, api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = self.send_request(method="apikey_delete", url_params=url_params, **kwargs)
        return response

    def whoami(self, *, token=None, api_key=None):
        """
        Returns information about the authorized principal. Works for tokens and API keys.
        The returned information includes the list of identities, a list of API keys and
        a list of sessions.
        """
        # Docstring is maintained separately
        headers = self._prepare_whoami(token=token, api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = self.send_request(method="whoami", **kwargs)
        return response

    def principal_info(self, *, principal_uid=None):
        # Docstring is maintained separately
        method = self._prepare_principal_info(principal_uid=principal_uid)
        response = self.send_request(method=method)
        return response

    def api_scopes(self, *, token=None, api_key=None):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        # Docstring is maintained separately
        headers = self._prepare_whoami(token=token, api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = self.send_request(method="api_scopes", **kwargs)
        return response

    def logout(self):
        """
        Log out. The API sends ``/auth/logout`` API request to the server and then clears
        local authorization key. Currently the ``/auth/logout`` API is intended for clearing
        browser cookies and serves no useful purpose for Python scripts and application.
        ``REManagerAPI.logout()`` is implemented for completeness. The same effect may
        be achieved by calling ``REManagerAPI.set_authorization_key()``, which does not call
        ``/auth/logout`` API, but clears the default security key.
        """
        # Docstring is maintained separately
        response = self.send_request(method="logout")
        self.set_authorization_key()  # Clear authorization keys
        return response

    def close(self):
        self._is_closing = True
        self._console_monitor.disable_wait(timeout=self._console_monitor_poll_period * 10)
        self._client.close()

    def __del__(self):
        self._is_closing = True


ReManagerComm_ZMQ_Threads.send_request.__doc__ = _doc_send_request
ReManagerComm_HTTP_Threads.send_request.__doc__ = _doc_send_request
ReManagerComm_ZMQ_Threads.close.__doc__ = _doc_close
ReManagerComm_HTTP_Threads.close.__doc__ = _doc_close
ReManagerComm_HTTP_Threads.login.__doc__ = _doc_api_login
ReManagerComm_HTTP_Threads.session_refresh.__doc__ = _doc_api_session_refresh

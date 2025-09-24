default_allow_request_fail_exceptions = True

default_status_expiration_period = 0.5  # s
default_status_polling_period = 1.0  # s

default_console_monitor_poll_timeout = 1.0  # s, 0MQ
default_console_monitor_poll_period = 0.5  # s, HTTP
default_console_monitor_max_msgs = 10000
default_console_monitor_max_lines = 1000

default_zmq_request_timeout_recv = 2.0  # s
default_zmq_request_timeout_send = 0.5  # s

default_http_request_timeout = 5.0  # s
default_http_login_timeout = 60.0  # s
default_http_server_uri = "http://localhost:60610"  # Default URI (for testing and evaluation)

# WebSocket defaults
default_ws_server_uri = "ws://localhost:60610/ws"  # Default WebSocket URI
default_ws_connection_timeout = 30.0  # s
default_ws_heartbeat_interval = 30.0  # s
default_ws_max_reconnect_attempts = 5
default_ws_reconnect_delay = 5.0  # s
default_ws_request_timeout = 10.0  # s
default_ws_ping_interval = 20.0  # s
default_ws_ping_timeout = 10.0  # s

default_wait_timeout = 600  # Timeout for wait operations in seconds

default_user_name = "Queue Server API User"
default_user_group = "primary"

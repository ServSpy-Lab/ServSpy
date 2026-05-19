The TCP Client APIs
===================

TCP Client setup API
--------------------

The TCP Client Setup API is used to create and manage a TCP client
that connects to a `TCP_Server_Base` instance and supports message
exchange, interactive console input, and file transfer operations.

.. code-block:: python

		class TCP_Client_Base:
				def __init__(
						self: Self, host: Any=None, client_host: Any='127.0.0.1',
						port: Any=65432, client_port: Any=None, timeout: Any=None,
						port_add_step: Any=1, max_thread_num: Any=10,
						is_input_command_in_console: Any=True, is_wait_server: Any=True,
						max_custom_workers: Any=10, is_extend_command: Any=False) -> None: ...

The parameters of the ``__init__`` method are as follows:

- ``host``: Optional server host to connect to. If ``None``, the
	client may be used in passive or temporary modes.
- ``client_host``: The local address to bind the client socket to.
- ``port``: The server port to connect to (default ``65432``).
- ``client_port``: Optional local port to bind the client to.
- ``timeout``: Optional socket timeout in seconds.
- ``port_add_step``: Step used when auto-allocating ephemeral ports.
- ``max_thread_num``: Maximum threads for client internal tasks.
- ``is_input_command_in_console``: Whether the client accepts console input.
- ``is_wait_server``: Whether the client should wait for server availability on connect.
- ``max_custom_workers``: Maximum workers for custom task executor.
- ``is_extend_command``: Enable extension command handling.

The client initializes internal resources such as an internal
thread-pool, command handler registries, port allocation helpers,
and file-transfer state needed for sending and receiving files.

Core connection methods
-----------------------

.. code-block:: python

		def connect(self: Self) -> None: ...
		def start_TCP_client(self: Self) -> None: ...
		def close(self: Self) -> None: ...

``connect`` opens a socket to the configured ``host`` and ``port``
and starts background message receivers. ``start_TCP_client`` is the
higher-level helper that manages connection retry logic according to
``is_wait_server``. ``close`` cleanly shuts down the client, closes
the socket, and releases any allocated ports.

Client I/O helpers
------------------

The client mirrors the server's simple I/O helpers for sending and
receiving newline-framed messages.

.. code-block:: python

		def send_message(self: Self, client_socket: Any, message: Any) -> bool: ...
		def recieve_message(self: Self, client_socket: Any, msg_length: int) -> bytes: ...

``send_message`` accepts ``str`` or ``bytes`` payloads, ensures a
trailing newline for string payloads, encodes to UTF-8, and calls
``sendall``. ``recieve_message`` is a thin wrapper over
``socket.recv`` for the requested number of bytes.

Message handling and commands
-----------------------------

The client processes server messages similarly to the server's
``handle_client`` loop. Messages beginning with ``/`` are treated as
commands and routed to ``handle_server_command``. Built-in client
commands and interactive behaviors include:

- ``/help``: print available client-side commands and usage hints.
- ``/time``: request or display server time responses.
- ``/quit``: disconnect the client.

The client exposes an extension API for registering custom commands:

.. code-block:: python

		def register_command(
				self: Self, command_name: Any, handler: Any,
				where_to_run: Any, run_in_thread: bool=False) -> bool: ...

Arguments are the same conceptually as the server-side API: the
``command_name`` should start with a slash, ``handler`` is a callable
that will be invoked with `(client_socket, client_address, command)`
for commands coming from the server, or with `(None, None, command)`
for console-run commands when ``where_to_run`` indicates a console
handler. The ``run_in_thread`` boolean controls whether the handler
is executed synchronously or on the client's thread pool.

The client uses ``_execute_custom_handler`` and ``submit_task`` to
invoke registered handlers the same way the server does; errors are
caught and logged and, when appropriate, sent back to the remote
peer.

File transfer flows (client perspective)
----------------------------------------

The client implements both sending files to the server (client-to-server)
and receiving files initiated by the server (server-to-client).

Client-to-server transfer flow:

1. The client issues a command such as ``/file <path> <client_id>`` or
	 ``/file_folder <path> <client_id>`` to the server socket.
2. The server responds with an internal coordination message:
	 ``/server_file_transfer_port <port> <client_id>`` providing the
	 ephemeral transfer port.
3. The client connects to the provided transfer port and performs the
	 length-prefixed filename and file-size handshake, then streams file
	 bytes to the server.

Server-to-client transfer flow:

- The server may instruct the client to prepare to receive files by
	sending transfer commands. The client will open a temporary
	listening socket (when required) and accept the incoming file
	transfer connection. Received files are written to the client's
	configured receive directory.

Low-level transfer helpers on the client include:

- ``file_transfer_mode``: client-side code that initiates an outgoing
	transfer to a remote transfer port.
- ``file_transfer_mode_recv``: client-side receive routine for
	handling incoming file data and metadata.
- Threaded helpers that start per-transfer threads and enforce the
	client's semaphore limits for concurrent file transfers.

Temporary servers and clients
-----------------------------

To avoid interfering with the main client socket, the client provides
convenience helpers to create short-lived temporary sockets used for
file transfers or other out-of-band operations:

.. code-block:: python

		def create_temporary_server(
				self: Self, handler: Any, port: Any=None, max_connections: int=1) -> Any: ...

		def create_temporary_client(
				self: Self, server_host: Any, server_port: Any,
				bind_port: Any=None, on_data: Any=None) -> Any: ...

These helpers return a running background thread or a tuple that
manages the temporary socket and a stop event so callers may interact
with the temporary connection and tear it down cleanly.

Port allocation and manual allocation mode
------------------------------------------

The client mirrors the server's port allocation APIs to acquire
ephemeral ports when needed. When ``is_hand_alloc_port`` is enabled,
the client will use lock files and a shared temp-info path to avoid
port collisions across processes. Key methods include:

- ``alloc_port`` / ``free_port``: top-level allocation and release.
- ``hand_alloc_port`` / ``hand_free_port``: manual allocation helpers
	that persist port state to files under the project temp info
	directory.

This mode is useful when multiple client instances on the same host
must coordinate ephemeral port usage for file-transfer sockets.

Helper APIs
-----------

- ``broadcast``: Not applicable for a single client, but the client
	exposes helpers to send messages to specific peers when acting as a
	temporary server.
- ``send_msg_to_specific_client``: used by the temporary-server helper
	to forward or inject messages to the main client loop.
- ``submit_task``: schedule work on the client's thread pool.

Interactive console
-------------------

When ``is_input_command_in_console`` is ``True``, the client spawns a
console loop accepting administrative or chat commands. Typical
commands are ``/help``, ``/quit``, and commands to start file
transfers. Console-run handlers are registered through
``register_command`` with ``where_to_run`` set to the console side.

Examples
--------

Basic client usage:

.. code-block:: python

		client = TCP_Client_Base(host='127.0.0.1', port=65432)
		client.connect()
		# send a simple message
		client.send_message(client.client_socket, 'hello server')

Initiate a file send to server:

.. code-block:: python

		client.send_message(client.client_socket, '/file /path/to/file 0')

This will trigger the server to return a transfer port and the
client's file transfer routines will connect and stream the file.

Notes and extension points
--------------------------

- The client supports registering custom command handlers via
	``register_command``; these can be used to add application-specific
	behavior without modifying the core library.
- Long-running or blocking handlers should be registered with
	``run_in_thread=True`` so the client's main receiver loop remains
	responsive.
- The file-transfer subsystem uses length-prefixed filename and size
	handshakes and enforces a semaphore limit configured by
	``max_file_transfer_thread_num`` to bound concurrent transfers.

See also
--------

For the server-side companion APIs and behavior, refer to
[TCP_Server_APIs.rst](TCP_Server_APIs.rst).

The TCP Client APIs
===================

TCP Client setup API
--------------------

The TCP Client Setup API is defined in the 
``TCP_Client_Base`` class. The client is used to 
connect to a ``TCP_Server_Base`` and participate 
in the protocol: message exchange, server-driven 
commands, interactive console commands and file 
transfers.

.. code-block:: python

    class TCP_Client_Base:
        def __init__(
            self: Self,
            host: Any=None,
            client_host: Any='127.0.0.1',
            port: Any=65432,
            client_port: Any=None,
            timeout: Any=None,
            port_add_step: Any=1,
            max_thread_num: Any=10,
            is_input_command_in_console: Any=True,
            is_wait_server: Any=True,
            max_custom_workers: Any=10,
            is_extend_command: Any=False) -> None:
            ...

The constructor initializes internal state and 
environment for the client. The parameters are:

- ``host``: remote server host to connect to. ``None`` is allowed for
  manual or temporary socket usage.
- ``client_host``: local interface used when binding client sockets.
- ``port``: remote server port (default ``65432``).
- ``client_port``: optional explicit local port to bind before connect.
- ``timeout``: optional connect timeout in seconds.
- ``port_add_step``: step used by manual port allocation bookkeeping.
- ``max_thread_num``: semaphore limit for concurrent file-transfer
  threads.
- ``is_input_command_in_console``: whether to run a console input
  thread for interactive commands.
- ``is_wait_server``: when ``True`` the client will retry connections
  and wait for the server to become available; otherwise failures are
  reported immediately.
- ``max_custom_workers``: maximum worker threads for registered
  custom commands.
- ``is_extend_command``: when ``False`` the constructor will call
  ``start_TCP_client()`` automatically; when ``True`` the caller must
  start the client lifecycle manually.

The constructor also prepares the project temp 
directory under ``.ServSpy/temp_info``, loads 
the command decode table from ``decode_command_table.json``, 
initializes the command/thread pools and semaphores, 
and sets up file transfer state (locks, counters and 
temp directories).

*Note: When ``is_extend_command`` is ``False`` the 
client will auto-start by calling ``start_TCP_client()`` 
inside the constructor.*

TCP Client connection API
-------------------------

The primary connection lifecycle methods are:

.. code-block:: python

    def connect(self: Self) -> bool:
        ...
    def receive_messages(self: Self) -> None:
        ...
    def close(self: Self) -> None:
        ...
    def start_TCP_client(self: Self) -> None:
        ...

``connect`` creates and configures a TCP socket, 
binds to ``client_host``/``client_port`` when 
specified, and connects to ``host:port``. On 
success it starts ``receive_messages`` in a background 
thread and registers the active socket in 
``self.client_socket``.

If ``is_wait_server`` is enabled the client will 
loop retrying when the server is not yet listening 
(connection refused or timeout). When ``is_wait_server`` 
is ``False`` connect errors return ``False`` and 
the caller may retry manually.

``receive_messages`` is the socket read loop. It 
uses ``recieve_message`` to read raw bytes, buffers 
until newline-terminated messages are available, 
decodes UTF-8 into text lines, prints/logs normal 
chat messages and dispatches commands (lines beginning 
with ``/``) to ``handle_server_command``.

``close`` stops the receive loop, closes sockets, 
cancels pending file-transfer operations and frees 
manually allocated ports when manual allocation 
is active.

TCP Client I/O API
------------------

Small helpers simplify socket I/O and framing:

.. code-block:: python

    def send_message(self, client_socket, message) -> bool:
        ...
    def recieve_message(self, client_socket, msg_length) -> bytes:
        ...

``send_message`` accepts ``str`` or ``bytes``. For strings it ensures a
trailing newline, encodes as UTF-8 and calls ``sendall`` to deliver the
whole payload. Errors are logged and the method returns ``False`` on
failure.

``recieve_message`` wraps a single ``socket.recv`` call and returns the
raw bytes read; framing and newline splitting are handled by the
``receive_messages`` loop.

TCP Client command API
----------------------

The client handles server-driven commands and supports a command
extension API allowing custom handlers to be registered for either
server-originated or console-side commands.

Built-in server-driven commands processed by ``handle_server_command``
include:

- ``/client_alloc_port_range <range>``: server-provided per-client port
  range enabling manual port allocation on the client.
- ``/client_alloc_port_range no_limit``: disable manual allocation and
  revert to dynamic OS-assigned ports.
- ``/server_file_transfer_port <port> <client_id>``: server announces
  an ephemeral port for an upcoming file transfer.
- ``/file ...`` and ``/file_folder ...``: server-initiated file /
  folder transfer commands that trigger the client receive flow.

Registering custom commands:

.. code-block:: python

    def register_command(self, command_name, handler, where_to_run,
                         run_in_thread=False) -> bool:
        ...

- ``command_name``: the command string (typically starting with ``/``).
- ``handler``: callable invoked for the command. For server-side
  commands handlers are called with ``(client_socket, client_address,
  command)``; console-side handlers receive ``(message, client_socket,
  client_id)``.
- ``where_to_run``: ``"server"`` to register a handler for commands
  received from the server; ``"client"`` to register a console-side
  command.
- ``run_in_thread``: if ``True``, the handler is executed on the
  client's thread pool via ``submit_task``; otherwise it runs
  synchronously in the reader/console thread.

Handlers are stored in two registries: ``_custom_handlers[0]`` for
server-side commands and ``_custom_handlers[1]`` for client/console
commands. ``_execute_custom_handler`` wraps handler calls, logs
exceptions and—when the command originates from the server—may
optionally send an error reply back.

Interactive console commands
----------------------------

When ``is_input_command_in_console`` is ``True``, the client starts an
interactive loop to accept user commands from stdin. Typical console
commands include:

- ``/quit``: send a quit command to the server and close the client.
- ``/file <path>``: request a file transfer to the server (client-side
  initiated send).
- ``/multiple_file <file1> <file2> ...``: request sending multiple
  files.
- ``/file_folder <folder_path>``: send a folder recursively.
- ``/multiple_file_folder <folder1> <folder2> ...``: send multiple
  folders.

If a console command was registered with ``where_to_run='client'``, the
registered handler will execute instead of the default network-send
behaviour.

TCP Client file transfer API
----------------------------

The client implements both outgoing (client-to-server) transfers and
incoming transfers initiated by the server. Transfers use a short TCP
handshake with length-prefixed metadata.

Client-to-server transfer flow:

1. The client issues ``/file`` or ``/file_folder`` to the server.
2. The server replies with ``/server_file_transfer_port <port>
   <client_id>`` announcing an ephemeral transfer port.
3. The client connects to the announced transfer port and performs the
   metadata handshake:

   - 4 bytes: filename length (network byte order)
   - filename bytes
   - 8 bytes: file size (network byte order)
   - file payload streamed in chunks

4. The sender waits for the remote sign/confirmation before closing
   the transfer and reporting success.

.. code-block:: python

    def file_transfer_mode(self, filename, server_address,
                           server_port, client_port) -> bool:
        ...

Server-to-client receive flow:

- The client allocates a local transfer port and opens a temporary
  listening socket (``file_transfer_client_recv_server_start``).
- The client sends the server the allocated port via
  ``/server_file_transfer_port <port> <client_id>``.
- The server connects and the client completes the length-prefixed
  receive using ``file_transfer_mode_recv`` which writes the received
  file(s) into the configured ``received_files`` directory by default.

.. code-block:: python

    def file_transfer_mode_recv(self, server_file_address,
                                server_file_port, client_socket,
                                client_id, new_save_path, file_name,
                                command) -> None:
        ...

The receive flow supports optional folder-relative save paths and
explicit target names.

Port allocation API
-------------------

The client supports two allocation modes: OS-managed dynamic ports
(default) and manual port allocation coordinated via server commands.

- ``alloc_port`` / ``free_port``: top-level allocation helpers. In
  automatic mode these return or accept ``0`` (letting the OS pick a
  port). In manual mode they coordinate via lock files under
  ``.ServSpy/temp_info``.
- ``hand_alloc_port`` / ``hand_free_port``: persistent allocation state
  stored in ``clients_port_info.log`` and synchronized with
  ``client_port_lock.lock`` to avoid cross-process conflicts.

When manual allocation is in use the client respects the per-client
ranges provided by the server and updates local bookkeeping files.

Temporary server and client helpers
-----------------------------------

For short-lived coordination sockets (for example the file transfer
listener), the client exposes convenience helpers:

.. code-block:: python

    def create_temporary_server(self, handler, port=None,
                                max_connections=1) -> socket:
        ...

    def create_temporary_client(self, server_host, server_port,
                                bind_port=None, on_data=None) -> socket:
        ...

These utilities create a lightweight server or client socket bound to
the client host and an available port. They run short-lived receiver
threads and invoke the provided callbacks on incoming data.

Helper APIs
-----------

- ``submit_task``: submit a callable to the client's internal thread
  pool and receive a ``Future``.
- ``_execute_custom_handler``: wrapper that runs registered command
  handlers, catches exceptions and optionally notifies the server of
  handler errors.
- ``register_command``: add dynamic command handling for server or
  console-side commands.

Examples
--------

Basic client usage:

.. code-block:: python

    client = TCP_Client_Base(host='127.0.0.1', port=65432)
    client.connect()
    client.send_message(client.client_socket, 'hello server')

Registering a server-side custom command:

.. code-block:: python

    def handle_ping(sock, addr, command):
        return 'pong'

    client.register_command('/ping', handle_ping, 'server')

Sending a file from the client console:

.. code-block:: python

    /file /path/to/file

See Also
--------

The server-side companion documentation: :doc:`TCP_Server_APIs`.

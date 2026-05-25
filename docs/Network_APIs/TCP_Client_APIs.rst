The TCP Client APIs
===================

TCP Client setup API
--------------------

The TCP Client Setup API is used to create a TCP 
client that connects to ``TCP_Server_Base`` and 
supports message exchange, extension commands, 
interactive console input, and file transfer.

.. code-block:: python

    class TCP_Client_Base:
        def __init__(
            self: Self, host: Any=None,
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

The constructor initializes the client environment 
and internal state. The arguments are:

- ``host``: Server host to connect to. If ``None``, the client may be
  used for temporary socket modes or manual connect management.
- ``client_host``: Local interface used when binding client sockets.
- ``port``: Server port to connect to (default ``65432``).
- ``client_port``: Optional explicit local port to bind before connect.
- ``timeout``: Optional socket timeout in seconds for connect operations.
- ``port_add_step``: Port step used by manual port allocation.
- ``max_thread_num``: Semaphore limit for concurrent file-transfer threads.
- ``is_input_command_in_console``: If ``True``, the client runs a console
  input loop for user commands.
- ``is_wait_server``: If ``True``, connect retry logic will wait for the
  server to become available instead of failing immediately.
- ``max_custom_workers``: Maximum worker threads for custom commands.
- ``is_extend_command``: If ``True``, the client does not auto-start.

The constructor also prepares the project temp directory 
under ``.ServSpy/temp_info``, loads the command decode 
table from ``decode_command_table.json``, initializes the 
thread pool, and sets up file-transfer state.

*Note: When ``is_extend_command`` is ``False``, the 
constructor automatically calls ``start_TCP_client()`` 
and begins the client lifecycle.*

TCP Client connection API
-------------------------

.. code-block:: python

    def connect(self: Self) -> bool:
        ...
    def receive_messages(self: Self) -> None:
        ...
    def close(self: Self) -> None:
        ...
    def start_TCP_client(self: Self) -> None:
        ...

``connect`` creates a TCP socket, binds to ``client_host`` 
and ``client_port`` if configured, and connects to 
``host:port``. On success, it starts ``receive_messages`` 
on a background thread.

If ``is_wait_server`` is ``True`` the client will 
keep waiting for the server to start when the 
connection is refused or times out. If 
``is_wait_server`` is ``False``, connection 
failures are reported and ``connect`` returns 
``False``.

``receive_messages`` reads UTF-8 data from the server 
socket into a newline-delimited buffer. Each complete 
message line is printed and commands starting with 
``/`` are passed to ``handle_server_command``.

``close`` stops the client, closes the socket, and 
releases allocated ports if manual port allocation 
is enabled.

TCP Client I/O API
------------------

The client provides small helpers for socket I/O.

.. code-block:: python

    def send_message(
        self: Self,
        client_socket: Any,
        message: Any) -> bool:
        ...
    def recieve_message(
        self: Self,
        client_socket: Any,
        msg_length: int) -> bytes:
        ...

``send_message`` accepts ``str`` or ``bytes`` 
payloads, appends a newline for text messages, 
encodes UTF-8, and sends the complete payload with
``sendall``.

``recieve_message`` wraps ``socket.recv`` and returns 
raw bytes from the socket.

TCP Client command API
----------------------

The client supports built-in commands from the server 
and custom extensible commands via ``register_command``.

Built-in server-driven commands handled by
``handle_server_command`` include:

- ``/client_alloc_port_range <range>``: enables manual port allocation
  using the server-provided per-client range.
- ``/client_alloc_port_range no_limit``: disables manual port
  allocation and allows the client to use default dynamic ports.
- ``/server_file_transfer_port <port> <client_id>``: received from the
  server to coordinate the ephemeral file transfer port.
- ``/file <...>``: triggers the client file send flow initiated by the
  server.
- ``/file_folder <...>``: triggers the client folder receive flow
  initiated by the server.

.. code-block:: python

    def register_command(
        self: Self,
        command_name: Any,
        handler: Any,
        where_to_run: Any,
        run_in_thread: bool=False) -> bool:
        ...

This API registers a custom command handler for 
either server-originated commands or console-side 
commands.

- ``command_name``: command string, typically starting with ``/``.
- ``handler``: callable invoked with ``(client_socket, client_address,
  command)`` for server-side commands or ``(message, client_socket,
  client_id)`` for console-side handlers.
- ``where_to_run``: ``"server"`` for commands received from the server,
  ``"client"`` for console-side commands.
- ``run_in_thread``: if ``True``, the handler runs on the client thread
  pool via ``submit_task``.

The client stores handlers in two registries:
``_custom_handlers[0]`` for server-side commands and
``_custom_handlers[1]`` for client console commands.
``_execute_custom_handler`` catches exceptions and optionally sends
error replies back to the server.

Interactive console commands
----------------------------

When ``is_input_command_in_console`` is ``True``, 
``interactive_mode`` reads user input and translates 
console commands into actions. Supported commands 
include:

- ``/quit``: send quit to the server and close the client.
- ``/file <path>``: send a file to the server using client-side transfer.
- ``/multiple_file <file1> <file2> ...``: send multiple files.
- ``/file_folder <folder_path>``: send a folder recursively.
- ``/multiple_file_folder <folder1> <folder2> ...``: send multiple folders.

If a console command is registered via ``register_command(...,
where_to_run='client')``, it is executed instead of 
the default send behavior.

TCP Client file transfer API
----------------------------

The client supports both outgoing transfers to the 
server and incoming transfers initiated by the 
server.

Client-to-server file transfer flow:

1. The client sends a command such as ``/file <path>`` or
   ``/file_folder <path>`` to the server.
2. The server responds with ``/server_file_transfer_port <port>
   <client_id>``.
3. The client connects to the provided ephemeral transfer port and
   begins the length-prefixed file metadata handshake.
4. The client sends the filename and size, then streams the file data.

.. code-block:: python

    def file_transfer_mode(
        self: Self,
        filename: Any,
        server_address: Any,
        server_port: Any,
        client_port: Any) -> bool:
        ...

The client waits for the server start-sign message before 
sending file metadata. It sends:

- 4 bytes: encoded filename length
- filename bytes
- 8 bytes: encoded file size
- file payload in chunks

It then waits for the server confirmation sign before 
reporting success.

Server-to-client file receive flow:

- ``file_transfer_client_recv_server_start`` allocates a local transfer
  port and opens a temporary listening socket.
- The client sends a ``/server_file_transfer_port`` reply to the server.
- The remote server connects and the client receives file metadata and
  data using ``file_transfer_mode_recv``.

.. code-block:: python

    def file_transfer_mode_recv(
        self: Self,
        server_file_address: Any,
        server_file_port: Any,
        client_socket: Any,
        client_id: Any,
        new_save_path: Any,
        file_name: Any,
        command: Any) -> None:
        ...

The receive flow writes incoming files to 
``received_files`` by default and supports 
optional folder-relative save paths or 
explicit names.

Port allocation API
-------------------

The client can allocate ports manually 
when the server requests a client port 
range. This is controlled by ``/client_alloc_port_range`` 
and the following methods:

- ``alloc_port`` / ``free_port``: top-level manual port allocation with
  lock file coordination.
- ``hand_alloc_port`` / ``hand_free_port``: persistent port allocation
  state under ``.ServSpy/temp_info/clients_port_info.log``.

Manual allocation uses ``client_port_lock.lock`` 
to serialize updates, so multiple client 
processes do not conflict when writing port 
state.

Temporary server and client helpers
-----------------------------------

The client offers lightweight helpers for 
temporary connections:

.. code-block:: python

    def create_temporary_server(
        self: Self,
        handler: Any,
        port: Any=None,
        max_connections: int=1) -> Any: ...

    def create_temporary_client(
        self: Self,
        server_host: Any,
        server_port: Any,
        bind_port: Any=None,
        on_data: Any=None) -> Any: ...

These helpers are useful for file-transfer 
coordination or short-lived peer interactions 
without interfering with the main client socket.

Helper APIs
-----------

- ``submit_task``: submit a function to the client's custom thread pool.
- ``_execute_custom_handler``: invoke registered handlers safely.
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

For the server-side companion APIs and behavior, refer to
:doc:`TCP_Server_APIs`.

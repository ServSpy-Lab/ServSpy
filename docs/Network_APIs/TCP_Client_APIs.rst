The TCP Client APIs
===================

TCP Client setup API
--------------------

The TCP Client Setup API is used to create a TCP client. 
The client in the protocol is usually used to connect to 
the TCP server and exchange data with the server.

.. code-block:: python

    class TCP_Client_Base:
        def __init__(
            self: Self,
            host: Any,
            client_host: Any,
            port: Any,
            client_port: Any,
            timeout: Any,
            port_add_step: Any,
            max_thread_num: Any,
            is_input_command_in_console: Any,
            is_wait_server: Any,
            max_custom_workers: Any,
            is_extend_command: Any=False) -> None: 
            ...

The TCP Client Setup API is defined in the ``TCP_Client_Base`` class.
The parameters of the ``__init__`` method are as follows:

- ``host``: The server host IP address to connect to.
- ``client_host``: The local host IP address to bind the client socket to.
- ``port``: The server port number to connect to.
- ``client_port``: The local port number to bind the client socket to (``None`` means let the OS choose).
- ``timeout``: The socket timeout in seconds for connection and receive operations (``None`` means no timeout).
- ``port_add_step``: The step size for incrementing the port number (used only in manual allocation mode).
- ``max_thread_num``: The maximum number of threads for concurrent file transfer operations.
- ``is_input_command_in_console``: A flag indicating whether to input commands in the console (interactive mode).
- ``is_wait_server``: A flag indicating whether to keep retrying connection until the server is available.
- ``max_custom_workers``: The maximum number of custom worker threads.

Every parameter has default values:

- ``host``: Default is ``None`` (must be provided before connecting)
- ``client_host``: Default is ``'127.0.0.1'``
- ``port``: Default is ``65432``
- ``client_port``: Default is ``None`` (OS assigns ephemeral port)
- ``timeout``: Default is ``None``
- ``port_add_step``: Default is ``1``
- ``max_thread_num``: Default is ``10``
- ``is_input_command_in_console``: Default is ``True``
- ``is_wait_server``: Default is ``True``
- ``max_custom_workers``: Default is ``10``
- ``is_extend_command``: Default is ``False`` 
  (when ``True``, ``__init__`` will not call ``start_TCP_client()`` automatically)

The TCP Client Setup API will initialize all the necessary 
parameters and resources for the TCP client.

*Note: In the main class of the TCP client setup API, 
we initialize the `start_TCP_client` method to setup 
all functions which are needed in the TCP client, 
including connecting to the server, handling incoming 
messages, and managing user input.* 

*Note: By default ``TCP_Client_Base.__init__`` calls 
``start_TCP_client()`` to connect and enter interactive 
mode. If you set ``is_extend_command=True``, the 
instance will not auto-start and you should call 
``start_TCP_client()`` manually when ready.*

*Note: If you set ``is_wait_server=True``, the ``timeout`` 
parameter must be ``None``. The constructor will raise 
a ``ValueError`` if ``is_wait_server`` is ``True`` and 
``timeout`` is not ``None``.*

.. code-block:: python

    def start_TCP_client(self: Self) -> Any:
        ...

In the `start_TCP_client` method, we first attempt to 
connect to the server by calling the `connect` method. 
If the connection fails and ``is_wait_server`` is ``True``, 
the client will keep retrying; otherwise it will exit.

*Note: The client socket created in the `start_TCP_client` 
method is based on IPv4 and uses the parameters 
``self.host`` and ``self.port`` which are provided when 
creating the client instance.*

Secondly, according to the ``self.is_input_command_in_console`` 
parameter, we will either start the interactive input loop 
(`interactive_mode`) or simply keep the connection alive 
(no console input).

After that, if the interactive mode is enabled, the client 
will read user input from the console and send messages 
to the server until the connection is closed.

*Note: There is a global variable ``self.running`` 
which is turned to ``True`` after the client successfully 
connects to the server. The ``self.running`` variable is 
used to control the main receive loop, and it will be 
turned to ``False`` when the client is shutting down.*

The `connect` method will try to establish a TCP connection 
to the server. If a ``client_port`` is specified, the client 
will bind to that local port before connecting. The method 
will handle timeouts and connection refused errors gracefully, 
especially when ``is_wait_server`` is enabled.

When the connection is established, a background thread 
`receive_messages` is started to continuously read data 
from the server.

So what can the setup function do if the connection fails?

First, if the connection attempt times out, the client 
will either wait and retry (if ``is_wait_server`` is ``True``) 
or exit with an error.

Secondly, if the server is not running (connection refused), 
the behaviour is the same: retry or exit based on 
``is_wait_server``.

If any other socket error occurs, the client will print 
the error message and return ``False``, and the 
`start_TCP_client` method will call ``sys.exit(1)``.

For shutting down the client, the `close` method is defined as:

.. code-block:: python

    def close(self: Self) -> None:
        ...

In the `close` method, we set ``self.running`` to ``False``, 
free any allocated ports by calling `free_port`, and then 
close the client socket. This ensures a clean disconnection.

*Note: The `free_port` method works similarly to the server 
side, releasing any manually allocated ports if manual 
allocation mode is enabled.*

.. _tcp-client-handling-information-api:

TCP Client handling information API
-----------------------------------

The client handling information API documents the core TCP 
client methods that manage the server connection, receive 
raw data, and send messages.

.. note::
   Unlike the server, the client maintains only a single 
   connection and does not provide broadcast or 
   ``send_msg_to_specific_client`` methods.

.. code-block:: python

    def receive_messages(
        self: Self) -> None:
        ...

`receive_messages` is the main background thread function 
in ``TCP_Client_Base``. It is started after a successful 
connection and is responsible for:

- continuously receiving raw bytes from the server socket using `receive_message`
- buffering incoming data until newline-terminated messages are complete
- splitting and processing each message line-by-line
- routing special commands (starting with ``/``) that come from the server to `handle_server_command`
- printing normal (non‑command) messages to the console with a ``[server]`` prefix
- handling connection resets and other socket errors, and cleaning up when the server closes the connection

.. code-block:: python

    def handle_server_command(
        self: Self,
        command: Any) -> None:
        ...

In `handle_server_command`, the client processes built-in 
commands sent by the server, such as:

- ``/client_alloc_port_range``: configures the clients manual 
  port allocation range based on server broadcast.
- ``/server_file_transfer_port``: receives the file transfer 
  port assigned by the server for an ongoing file operation.
- ``/file`` and ``/file_folder``: handle file transfer requests 
  initiated by the server (server-to-client transfers).

If you have registered custom commands using the command 
extension API, `handle_server_command` will also check 
if the incoming command matches any registered handler 
and execute it accordingly.

*Note: For more details of the command extension API, 
see the :ref:`tcp-client-command-api` section.*

- logging errors and disconnecting when the server closes the socket.

.. code-block:: python

    def receive_message(
        self: Self,
        client_socket: Any,
        msg_length: Int) -> Any:
        ...

`receive_message` is identical to the server version: 
it reads up to ``msg_length`` bytes from the given 
socket and returns the raw byte payload. Message decoding 
and newline framing are handled by the caller.

.. code-block:: python

    def send_message(
        self: Self,
        client_socket: Any,
        message: Any) -> True|False:
        ...

`send_message` sends data from the client to the server.
It verifies the client is still running and the socket is valid, then:

- accepts both ``str`` and ``bytes`` message payloads
- trims string payloads and appends a newline if missing
- encodes string payloads as UTF-8
- sends the complete message with ``client_socket.sendall(data)``
- returns ``True`` on success, otherwise logs the error and returns ``False``

The client also provides an interactive input loop (`interactive_mode`) 
that reads user input from the console and sends messages 
to the server.

.. _tcp-client-command-api:

TCP Client command API
----------------------

The client supports both built-in commands that the user can 
type in the console, and a command extension API similar to 
the server. The main entry point for incoming server commands 
is `handle_server_command`, while user-typed commands are 
processed in `interactive_mode`.

The client supports two modes of operation: interactive console 
input (when ``is_input_command_in_console`` is ``True``) or 
programmatic control (when it is ``False``).

Built-in client console commands (user-typed) include:

- ``/quit``: sends a quit message to the server and closes the connection.
- ``/file <file_path>``: starts a file transfer from client to server.
- ``/multiple_file <file1> <file2> ...``: sends multiple files from 
  client to server (each in its own thread, respecting the semaphore limit).
- ``/file_folder <folder_path>``: sends an entire folder from 
  client to server, preserving the directory structure.
- ``/multiple_file_folder <folder1> <folder2> ...``: sends multiple 
  folders from client to server.

*Note: Unlike the server, the client does not have built-in 
``/help``, ``/time``, or ``/clients`` commands because those 
are typically handled by the server. The client's ``/help`` 
command is not implemented; users should refer to the server 
documentation for available commands.*

If a user types a command that is not built-in, the client 
will check if it matches any registered custom commands 
(see command extension API below). If it does, the client 
will call the associated handler; otherwise the message 
is sent as a normal chat message to the server.

The command extension API for the client is defined as:

.. code-block:: python

    def register_command(
        self: Self,
        command_name: Any,
        handler: Any,
        where_to_run: Any,
        run_in_thread: Any=False) -> bool:
        ...

The arguments of the `register_command` function are the same 
as on the server side:

- ``command_name``: The name of the command to register 
  (should start with a slash, e.g., ``/mycmd``).
- ``handler``: The function to call when the command is received. 
  The handler must accept three parameters: ``client_socket``, ``client_address``, and ``command``.
- ``where_to_run``: Specifies where the command should be executed. 
  Valid values are ``"server"`` (command sent from the server) or ``"client"`` (command typed in the client's console).
- ``run_in_thread``: A boolean indicating whether to run the handler 
  in a separate thread from the thread pool.

*Note: The client stores registered commands in the same 
structure as the server: ``self._custom_handlers = [{}, {}]``, 
where index 0 is for commands coming from the server, and 
index 1 is for commands typed in the client console.*

The client also provides the `submit_task` method to submit 
functions to its internal thread pool executor, and 
`_execute_custom_handler` to safely execute registered 
handlers with error handling.

.. code-block:: python

    def submit_task(
        self: Self,
        func: Any,
        *args: Any,
        **kwargs: Any) -> None:
        ...

The `submit_task` method works identically to the server 
version: it submits a callable to the client's thread pool, 
using a semaphore to limit concurrency to ``max_custom_workers``.

Temporary server and client creation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The client also includes temporary TCP server and client 
creation APIs. They are similar to those in the server class 
but use `self.client_host` as the local binding address.

.. code-block:: python

    def create_temporary_server(
        self: Self,
        handler: Any,
        port: Any=None,
        max_connections: Any=1) -> Any:
        ...

`create_temporary_server` binds to ``(self.client_host, port)``. 
If ``port`` is ``None``, it calls ``self.palloc()`` to obtain 
a port (in manual mode) or returns ``0`` (OS-assigned). It 
returns a tuple ``(port, server_thread, stop_event)``.

.. code-block:: python

    def create_temporary_client(
        self: Self,
        server_host: Any,
        server_port: Any,
        bind_port: Any=None,
        on_data: Any=None) -> Any:
        ...

`create_temporary_client` connects to the specified server. 
If ``bind_port`` is given, it binds to ``(self.client_host, bind_port)``. 
If ``bind_port`` is ``None``, it obtains a port via ``self.palloc()`` 
and binds automatically. It returns a tuple 
``(client_sock, recv_thread, stop_event)``.

These methods allow the client to act as a temporary server 
or to spawn a separate client connection for auxiliary tasks 
(such as file transfers), without interfering with the main 
connection.

TCP Client console commands (interactive mode)
-----------------------------------------------

When the client is started with ``is_input_command_in_console=True`` 
(the default), the `interactive_mode` method is invoked. 
This method reads lines from standard input and processes them.

Supported console commands (user-typed) include:

- ``/quit``: closes the connection and exits the client.
- ``/file <file_path>``: sends a single file to the server.
- ``/multiple_file <file1> <file2> ...``: sends multiple files to the server concurrently (limited by ``max_thread_num``).
- ``/file_folder <folder_path>``: sends an entire folder to the server, recursively.
- ``/multiple_file_folder <folder1> <folder2> ...``: sends multiple folders to the server.
- Any other text not starting with ``/`` is sent as a normal chat message to the server.

.. note::
   The client does not have a built-in ``/help`` command. 
   Please refer to the server's help for available commands 
   (e.g., by typing ``/help`` after connecting to the server).

If a user types a custom command that has been registered with 
``register_command(..., where_to_run="client")``, the client 
will execute the associated handler (synchronously or in a 
thread, as configured).

*Note: The client will print an error message for unknown 
commands that start with ``/``.*

Example interactive session::

    connecting to 127.0.0.1:65432...
    connect success! type '/help' to get help.

    Hello server
    [server] msg send: Hello server
    /file mydoc.txt
    [server] file mydoc.txt received
    /quit
    connection closed

TCP Client file transfer API
----------------------------

The TCP client contains a file transfer subsystem that supports 
both client-to-server and server-to-client transfers, using 
the same underlying protocol as the server.

As with the server documentation, only the list of APIs is 
provided here. For detailed internal flow, please refer to 
the server documentation or the source code.

The file transfer API for the client includes:

The basic function for client-to-server file transfer is:

.. code-block:: python

    def file_transfer_client_recv_client_start(
        self: Self,
        message: Any,
        file_folder_abspath: Any=None) -> None|False:
        ...

The thread-safe version (recommended for direct calls) is:

.. code-block:: python

    def file_transfer_client_recv_client_start_thread(
        self: Self,
        message: Any,
        file_folder_abspath: Any=None) -> None:
        ...

The folder transfer function (client-to-server) is:

.. code-block:: python

    def folder_file_transfer_client_recv_client_start(
        self: Self,
        message: Any) -> None|False:
        ...

The multiple files transfer function (client-to-server) is:

.. code-block:: python

    def multiple_file_transfer_client_recv_client_start(
        self: Self,
        message: Any) -> None:
        ...

The multiple folders transfer function is:

.. code-block:: python

    def multiple_folder_file_transfer_client_recv_client_start(
        self: Self,
        message: Any) -> None:
        ...

For server-initiated transfers (server-to-client), the client 
provides these handlers:

.. code-block:: python

    def file_transfer_client_recv_server_start(
        self: Self,
        client_id: Any,
        client_socket: Any,
        command: Any,
        new_save_path: Any=None,
        file_name: Any=None) -> None:
        ...

    def file_transfer_client_recv_server_start_thread(
        self: Self,
        client_id: Any,
        client_socket: Any,
        command: Any) -> None:
        ...

    def file_folder_transfer_client_recv_server_start_thread(
        self: Self,
        command: Any,
        client_id: Any,
        client_socket: Any) -> None:
        ...

The low-level receive mode function is:

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

And the low-level send mode function is:

.. code-block:: python

    def file_transfer_mode(
        self: Self,
        filename: Any,
        server_address: Any,
        server_port: Any,
        client_port: Any) -> True|False:
        ...

We recommend that for client-to-server file transfers, 
you use the console commands (``/file``, ``/file_folder``, 
etc.) rather than calling these APIs directly, because 
the console commands already handle threading and semaphore 
limits correctly. If you need to call the API directly, 
use the `_thread` versions (e.g., 
`file_transfer_client_recv_client_start_thread`) to avoid 
blocking the main thread.

*Note: The file transfer API functions follow the same 
handshake protocol as the server: the initiator sends 
a command over the main connection, then a temporary 
port is negotiated, and the actual file data is transferred 
over a separate TCP connection.*

Port allocation API
-------------------

The client port allocation APIs are nearly identical to those 
of the server. They allow you to allocate ephemeral ports 
either automatically (by returning 0, letting the OS choose) 
or manually within a configured range.

To change the port allocation mode, the client listens to 
the server's broadcast of ``/client_alloc_port_range``. 
When the server sends that command with a number, the client 
sets ``self.is_hand_alloc_port = True`` and configures the 
range. If the server sends ``NO_LIMIT``, the client uses 
automatic allocation (return 0 from allocation calls).

In manual allocation mode, the port range is determined 
by the server's broadcast value. The client maintains its 
own range based on ``self.port`` (the server port) and 
the received range. The minimum allocatable port is 
``self.port - self.port_add_step * each_client_port_range``, 
and the maximum is 
``self.port + 1 + self.port_add_step * each_client_port_range``.

The main methods for port allocation are:

.. code-block:: python

    def palloc(self: Self) -> int:
        ...

`palloc` returns an available port (either 0 for automatic 
mode, or a concrete port number from the manual range). 
It internally calls `file_palloc` (additive allocation) 
and `spy_palloc` (subtractive allocation) in a loop.

.. code-block:: python

    def pfree(
        self: Self,
        port: int) -> None|int:
        ...

`pfree` releases a previously allocated port. In manual 
mode, it removes the port from the internal list and 
adjusts the latest port pointers. In automatic mode, 
it does nothing.

As with the server, the automatic mode (returning 0) is 
recommended for most use cases because it avoids port 
conflicts and simplifies code. Manual mode is provided 
for environments where port ranges must be strictly 
controlled (e.g., firewalls or testing).

TCP Client APIs table
---------------------

In short, the table of contents of the public APIs 
are as follows:

1. The client setup APIs:
    - `TCP_Client_Base`
    - `start_TCP_client`
    - `connect`
    - `close`

2. The client handling information APIs:
    - `receive_messages`
    - `handle_server_command`
    - `receive_message`
    - `send_message`
    - `interactive_mode`

3. The client command APIs:
    - `register_command`
    - `_execute_custom_handler`
    - `submit_task`
    - `create_temporary_server`
    - `create_temporary_client`

4. The client file transfer APIs:
    - `file_transfer_client_recv_client_start`
    - `file_transfer_client_recv_client_start_thread`
    - `folder_file_transfer_client_recv_client_start`
    - `multiple_file_transfer_client_recv_client_start`
    - `multiple_folder_file_transfer_client_recv_client_start`
    - `file_transfer_client_recv_server_start`
    - `file_transfer_client_recv_server_start_thread`
    - `file_folder_transfer_client_recv_server_start_thread`
    - `file_transfer_mode_recv`
    - `file_transfer_mode`

5. The client console commands (interactive mode):
    - `/quit`
    - `/file`
    - `/multiple_file`
    - `/file_folder`
    - `/multiple_file_folder`

See Also
--------

- :doc:`TCP_Server_APIs` — TCP server.
- :doc:`UDP_APIs` — UDP endpoint.

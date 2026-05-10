The TCP Server APIs
===================

TCP Server setup API
--------------------

The TCP Server Setup API is used to create a TCP server. 
The server in the protocal is usually used to connect and 
listen to the TCP clients and handle the data from the 
clients.

.. code-block:: python

    class TCP_Server_Base:
        def __init__(
            self: Self, host: Any, port: Any, max_clients: Any,
            port_add_step: Any, port_range_num: Any,
            max_file_transfer_thread_num: Any, is_hand_alloc_port: Any,
            is_input_command_in_console: Any, max_custom_workers: Any) -> None: 
            ...

The TCP Server Setup API is defined in the ``TCP_Server_Base`` class.
The parameters of the ``__init__`` method are as follows:

- ``host``: The host IP address to bind the TCP server to.
- ``port``: The port number to bind the TCP server to.
- ``max_clients``: The maximum number of concurrent clients the server can handle.
- ``port_add_step``: The step size for incrementing the port number.
- ``port_range_num``: The number of ports to check in the range.
- ``max_file_transfer_thread_num``: The maximum number of threads for file transfer operations.
- ``is_hand_alloc_port``: A flag indicating whether to manually allocate the port.
- ``is_input_command_in_console``: A flag indicating whether to input commands in the console.
- ``max_custom_workers``: The maximum number of custom worker threads.

Every parameters are all have default values:

- ``host``: Default is ``'127.0.0.1'``
- ``port``: Default is ``65432``
- ``max_clients``: Default is ``10``
- ``port_add_step``: Default is ``1``
- ``port_range_num``: Default is ``100``
- ``max_file_transfer_thread_num``: Default is ``10``
- ``is_hand_alloc_port``: Default is ``False``
- ``is_input_command_in_console``: Default is ``True``
- ``max_custom_workers``: Default is ``10``

The TCP Server Setup API will initialize all the necessary 
parameters and resources for the TCP server.

*Note: In the main class of the TCP server setup API, 
we initialize the `start_TCP_Server` method to setup 
all functions which are needed in the TCP server, 
including the server socket or handle clients etc..* 

.. code-block:: python

    def start_TCP_Server(self: Self) -> Any: ...

In the `start_TCP_Server` method, we first create a 
TCP server socket and bind it to the ``self.host`` and 
``self.port`` which are initialized in the ``__init__`` method. 

*Note: The server socket which is set up in the `start_TCP_Server` 
method is based on IPv4 form.*

Secondly, according to the ``self.is_input_command_in_console`` 
parameter, we will start a thread to listen to the console 
input of the server or not.

After that, a main loop to accept clients will be started.

*Note: there is another gloable variable ``self.running`` 
which is turned to ``True`` after the server socket is 
successfully created. The ``self.running`` variable is 
used to control the main loop of the TCP server, and it 
will be turned to ``False`` when the server is shutting down.*

The main loop of the TCP setup server function will first judge 
if the number of the clients which are connected to the server 
is over the max clients number or not. By the way, the max clients 
number limit is defined by the args of the `TCP_Server_Base` 
class, the ``self.max_clients`` variable which initialized in the 
class.

If the number of the clients is already over the limit of the connect 
number, the server will send a overload message and close the connect. 
But if it didn't over the limit, the server will setup a clients 
handlers function `handle_client` and the server handler function 
is defined as:

.. code-block:: python

    def handle_client(
        self: Self, client_socket: Any, client_address: Any) -> Any: ...

*Note: For more details of the `handle_client` function, please visit ...*

So what can the setup function do if the it run failed? 

First, the try and except code block in the main server loop 
will detect if the error is an ``OSError``. If it is, the 
main loop will exit directly.

Secondly, if the error is from the network socket, it will first 
output the error message and also stop the server by calling 
the function `stop`. And the stop function has been defined as: 

.. code-block:: python

    def stop(self: Self) -> None: ...

For the stop tcp server function, it first set the ``self.running`` 
variable to False, for stop the main loop of the server. 
After that, it calls the `free_port` function to free the 
port which has been alloced. And the `free_port` has been 
defined as:

.. code-block:: python

    def free_port(self: Self) -> None: ...

*Note: For more details of the `free_port` function, please visit ...*

At the end of the operations, the TCP server will close all 
of the sockets of clients which are accounted in the dictionary 
variable ``self.clients`` and also close the server socket.

*Note: The ``self.clients`` variable is a dictionary which is 
used to store the client sockets and their corresponding 
addresses. The key of the dictionary is the client socket, 
and the value is the client address. It has been defined 
in the ``__init__`` method.*

.. code-block:: python

    from datetime import datetime
    # client_address: tuple e.g. ('127.0.0.1', 12345)
    # client_socket: socket.socket
    # client_id = f"{client_address[0]}:{client_address[1]}"
    self.clients[client_address] = {
        'socket': client_socket,
        'address': client_address,
        'id': client_id,
        'connected_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

TCP Server handling information API
-----------------------------------

The server handling information API documents the core TCP 
server methods that manage client sockets, receive raw data, 
and send messages.

.. code-block:: python

    def handle_client(self: Self, client_socket: Any, client_address: Any) -> None:
        ...

`handle_client` is the main per-client handler in 
``TCP_Server_Base``. It is invoked after a client 
connection is accepted and is responsible for:

- adding the client entry into ``self.clients`` with socket, address, id, and connected time
- printing connection information and current client count
- sending a welcome message to the client
- broadcasting ``/client_alloc_port_range`` information to all clients depending on port allocation mode

*Note: You can specify the port allocation mode in 
the arguments which has been defined in the 
``TCP_Server_Base`` class. The args which you can 
change are ``port_add_step``, ``port_range_num`` 
and ``is_hand_alloc_port``.*

- receiving raw bytes from the socket using `recieve_message`
- buffering incoming data until newline-terminated messages are complete
- splitting and processing each message line-by-line
- routing special commands beginning with ``/`` to `handle_command`

The `handle_command` function is defined as: 

.. code-block:: python

    def handle_command(self: Self, client_socket: Any, client_address: Any, command: Any) -> None:
        ...

In `handle_command`, there are variable conditional 
branches to handle built-in commands like ``/help``, 
``/time``, ``/clients``, ``/quit``, and some file 
transfer commands. If you already added more commands 
by the command extension API, the function will 
determine if the inputed message matched the extension 
commands.

*Note: For more details of the command extension API, 
please visit ...*

- logging normal chat messages and acknowledging receipt
- removing the client from ``self.clients`` and closing the socket when the client disconnects or an error occurs

.. code-block:: python

    def recieve_message(self: Self, client_socket: Any, msg_length: Int) -> Any:
        ...

`recieve_message` is a thin wrapper around socket 
receive operations. It reads up to ``msg_length`` 
bytes from the given ``client_socket`` and 
returns the raw byte payload. Message decoding 
and newline message framing are handled by the 
caller.

.. code-block:: python

    def send_message(self: Self, client_socket: Any, message: Any) -> True|False:
        ...

`send_message` sends data back to a specific connected client.
It verifies the server is running and the socket is valid, then:

- accepts both ``str`` and ``bytes`` message payloads
- trims string payloads and appends a newline if missing
- encodes string payloads as UTF-8
- sends the complete message with ``client_socket.sendall(data)``
- returns ``True`` on success, otherwise logs the error and returns ``False``

These methods form the server's client I/O loop 
and ensure reliable message exchange for connected 
TCP clients.

TCP Server command API
----------------------

The server supports several built-in client commands and a command dispatcher.
The main entry point is the ``handle_command`` method, which is invoked for any
message starting with ``/``.

Built-in client commands include:

- ``/help``: returns the available command list and usage hints.
- ``/time``: returns the current server time.
- ``/clients``: returns the list of connected client IDs.
- ``/quit``: returns a goodbye message and disconnects the client.
- ``/file <file_path> <client_id>``: starts a file transfer request from client to server.
- ``/file_folder <folder_path> <client_id>``: starts a folder transfer request from client to server.
- ``/server_file_transfer_port <port> <client_id>``: internal protocol message used to coordinate file transfer ports.

If a command is not recognized by the built-in handler, ``handle_command`` will
attempt to dispatch it to a custom registered command handler.

.. code-block:: python

    def register_command(
        self: Self, command_name: Any, handler: Any,
        where_to_run: Any, run_in_thread: Any=False) -> bool: ...

This extension API allows server-side and console-side custom commands to be
registered dynamically. Valid values for ``where_to_run`` are ``"server"`` and
``"client"``.

TCP Server console commands
---------------------------

The server console input thread accepts administrative commands when
``is_input_command_in_console`` is ``True``. Supported console commands include:

- ``/stop``: stops the server and closes all active connections.
- ``/status``: prints the current connection count and running state.
- ``/clients``: prints the connected clients and their connection times.
- ``/send_msg <message...> <client_id1> <client_id2> ...``: sends one or more messages to specific clients.
- ``/file <file_path> <client_id>``: sends a file from the server to a specific client.
- ``/file_folder <folder_path> <client_id>``: sends a folder from the server to a specific client.
- ``/multiple_file_multiple_client <file1> <file2> ... <client1> <client2> ...``: sends multiple files to multiple clients.
- ``/diff_multiple_file_diff_multiple_client <file1> <file2> ... <client1> <client2> ...``: sends different file lists to different clients.
- ``/help``: prints a help summary of console commands.

These console commands make it easy to manage the active server and perform
server-initiated file transfers without modifying the code.

TCP Server file transfer API
----------------------------

The TCP server contains a file transfer subsystem that supports both client-to-server
and server-to-client transfers.

Client-to-server transfer flow:

1. The client sends ``/file`` or ``/file_folder`` to request a transfer.
2. ``handle_command`` starts a dedicated file-server thread using
   ``file_transfer_server_recv_server_start_thread``.
3. The server allocates an ephemeral transfer port with ``palloc`` and sends
   ``/server_file_transfer_port <port> <client_id>`` back to the client.
4. The client connects to that transfer port and sends file metadata, including
   length-prefixed filename and file size.
5. The server receives the file and writes it under ``received_files``.

Server-to-client transfer flow:

- ``file_transfer_server_recv_client_start`` is used to initiate outgoing
  transfers from server to a connected client.
- The server sends transfer commands to the client socket and waits for the
  client to establish the file transfer connection.
- Folder transfers are performed recursively, with each file transfer respecting
  ``self.max_file_transfer_thread_num`` and the configured semaphore limit.

Common file transfer helper methods include:

- ``file_transfer_server_recv_server_start``: receives file data from a client.
- ``file_transfer_server_recv_client_start``: sends a file or folder to a client.
- ``file_transfer_mode``: performs the low-level client-side transfer handshake.
- ``file_transfer_mode_recv``: performs the low-level receive-side transfer handshake.

Port allocation API
-------------------

When ``is_hand_alloc_port`` is ``True``, the server uses manual port allocation
and lock files to avoid conflicts across multiple server instances. The relevant
methods are:

- ``alloc_port``: allocate a port range for the server.
- ``free_port``: release the allocated port range when the server stops.
- ``hand_alloc_port`` and ``hand_free_port``: internal helpers used by the manual allocation flow.

This mode is useful when the server must reserve a controlled range of ports
for client-file transfers or when multiple server processes share the same host.

TCP Server helper APIs
----------------------

The following helper methods are also available on ``TCP_Server_Base``:

- ``broadcast(self, message, exclude_client=None)``: broadcast a message to all connected clients.
- ``send_msg_to_specific_client(self, message)``: send a message to one or more specific clients by address.
- ``submit_task(self, func, *args, **kwargs)``: submit work to the server's internal thread pool.
- ``create_temporary_server(self, handler, port=None, max_connections=1)``: start a temporary TCP server for short-lived tasks.
- ``create_temporary_client(self, server_host, server_port, bind_port=None, on_data=None)``: start a temporary client that receives data asynchronously.

These APIs make it easier to extend the base TCP server for custom command handling,
background tasks, and temporary connections.

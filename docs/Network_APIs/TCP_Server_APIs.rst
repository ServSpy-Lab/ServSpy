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
            self: Self,
            host: Any,
            port: Any,
            max_clients: Any,
            port_add_step: Any,
            port_range_num: Any,
            max_file_transfer_thread_num: Any,
            is_hand_alloc_port: Any,
            is_input_command_in_console: Any,
            max_custom_workers: Any) -> None: 
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

    def start_TCP_Server(self: Self) -> Any:
        ...

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
        self: Self, client_socket: Any, client_address: Any) -> Any:
        ...

*Note: For more details of the `handle_client` function, please visit ...*

So what can the setup function do if the it run failed? 

First, the try and except code block in the main server loop 
will detect if the error is an ``OSError``. If it is, the 
main loop will exit directly.

Secondly, if the error is from the network socket, it will first 
output the error message and also stop the server by calling 
the function `stop`. And the stop function has been defined as: 

.. code-block:: python

    def stop(self: Self) -> None:
        ...

For the stop tcp server function, it first set the ``self.running`` 
variable to False, for stop the main loop of the server. 
After that, it calls the `free_port` function to free the 
port which has been alloced. And the `free_port` has been 
defined as:

.. code-block:: python

    def free_port(self: Self) -> None:
        ...

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

    def handle_client(
        self: Self,
        client_socket: Any,
        client_address: Any) -> None:
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

    def handle_command(
        self: Self,
        client_socket: Any,
        client_address: Any,
        command: Any) -> None:
        ...

In `handle_command`, there are variable conditional 
branches to handle built-in commands like ``/help``, 
``/time``, ``/clients``, ``/quit``, and some file 
transfer commands. If you already added more commands 
by the command extension API, the function will 
determine if the inputed message matched the extension 
commands.

*Note: For more details of the command extension API, 
and the built-in commands, please visit ...*

- logging normal chat messages and acknowledging receipt
- removing the client from ``self.clients`` and closing the socket when the client disconnects or an error occurs

.. code-block:: python

    def recieve_message(
        self: Self,
        client_socket: Any,
        msg_length: Int) -> Any:
        ...

`recieve_message` is a thin wrapper around socket 
receive operations. It reads up to ``msg_length`` 
bytes from the given ``client_socket`` and 
returns the raw byte payload. Message decoding 
and newline message framing are handled by the 
caller.

.. code-block:: python

    def send_message(
        self: Self,
        client_socket: Any,
        message: Any) -> True|False:
        ...

`send_message` sends data back to a specific connected client.
It verifies the server is running and the socket is valid, then:

- accepts both ``str`` and ``bytes`` message payloads
- trims string payloads and appends a newline if missing
- encodes string payloads as UTF-8
- sends the complete message with ``client_socket.sendall(data)``
- returns ``True`` on success, otherwise logs the error and returns ``False``

And there are also some other functions which are 
used to send message in bulk to the clients, such 
as the `broadcast` function and the `send_msg_to_specific_client` 
function.

.. code-block:: python

    def broadcast(
        self: Self,
        message: Any,
        exclude_client: Any=None) -> None:
        ...

In `broadcast` function, it will send a message to all 
the clients which are in the ``self.clients`` variable, 
also delete the clients which are already disconnected 
with the server. And if the ``exclude_client`` parameter 
is not ``None``, the server will exclude the client 
which is specified by the ``exclude_client`` parameter 
when sending the message.

.. code-block:: python

    def send_msg_to_specific_client(
        self: Self,
        message: Any) -> None:
        ...

The `send_msg_to_specific_client` function is used to send 
one or more message to one or more specific clients by their 
client IDs. And the ``message`` args should be input a send 
message command.

These methods form the server's client I/O loop 
and ensure reliable message exchange for connected 
TCP clients.

TCP Server command API
----------------------

The server supports several built-in commands 
and a command extension API. The main entry 
point is the `handle_command` method, which 
is invoked for any message starting with ``/``.

We support two solutions for command handling, 
one is input a command in the console, and 
the other is recieving a command from other 
clients, and you can also call the functions 
which are defined for the commands in the code.

*Note: You can select the solution which you 
want to use by changing the args of the 
`TCP_Server_Base` class, the arg is 
``is_input_command_in_console``. ``True`` is 
allow the server to input the command in 
console, while ``False`` is don't allow.*

Built-in client commands include:

- ``/help``: returns the available command list and usage hints.
- ``/time``: returns the current server time.
- ``/clients``: returns the list of connected client IDs.
- ``/quit``: returns a goodbye message and disconnects the client.
- ``/file <file_path> <client_id>``: starts a file transfer request from client to server.
- ``/file_folder <folder_path> <client_id>``: starts a folder transfer request from client to server.
- ``/server_file_transfer_port <port> <client_id>``: internal protocol message used to coordinate file transfer ports.

In `handle_command`, the server will first 
check if the command matches any built-in commands. 
If it dose, the `handle_command` will call the 
functions which are defined for the commands.

If a command is not recognized by the built-in handler, 
`handle_command` will check if it matches any 
registered custom commands from the command extension 
API. If the command is already registered, the 
`handle_command` will call the function defined 
for that command. The command extension API is 
defined as:

.. code-block:: python

    def register_command(
        self: Self,
        command_name: Any,
        handler: Any,
        where_to_run: Any,
        run_in_thread: Any=False) -> bool:
        ...

The args of the `register_command` function 
are as follows:

- ``command_name``: The name of the command to register.

*Note: The ``command_name`` should start with a slash 
(e.g., ``/my_command``) to be recognized as a command.*

- ``handler``: The function to call when the command is received.

*Note: The ``handler`` function must have and only have three 
parameters which are ``client_socket``, ``client_address``, 
and ``command``. ``client_socket`` will be accepted as the 
network socket object who sent the command, ``client_address`` 
will be accepted as the address of the client that sent the 
command, while the ``command`` parameter will contain the actual 
command string.*

- ``where_to_run``: Specifies where the command should be executed.
- ``run_in_thread``: A boolean indicating whether to run the command in a separate thread.

This extension API allows server-side and 
console-side custom commands to be registered 
dynamically. Valid values for ``where_to_run`` 
are ``"server"`` and ``"client"``. The ``"server"`` 
means the command will be handled when a client 
sends the command, while the ``"client"`` means 
the command will be handled when the server input 
the command in console.

*Note: It's true that the valid values for ``where_to_run`` 
are too strange, but we stile didn't find a better way to 
define that.*

The ways to run the command will be different 
according to the args ``run_in_thread``. If 
``run_in_thread`` is ``True``, the command handler 
will be executed in a separate thread from the 
server's thread pool. If ``run_in_thread`` is 
``False``, the command handler will be executed 
synchronously in the main server thread.

*Note: We store the registered commands in a list variable 
with two dictionary in its inner layer, and the list variable 
is defined as ``self._custom_handlers`` which initialized in 
the `__init__` method. The command and its handler will be 
stored in the one of the dictionaries according to the value 
of ``where_to_run``. For ``"server"``, it will be stored in 
the first dictionary, other wise in the second dictionary. 
And the key of the dictionaries are all the command name, 
and the value is another dictionary containing the handler 
function. And there is also another list variable defined as 
``self._custom_handler_threaded`` which initialized in the 
`__init__` method, it contains all the commands that should 
be run in a separate thread or not.*

.. code-block:: python

    self._custom_handlers = [{}, {}]
    self._custom_handler_threaded = [{}, {}]

After that, the command handler will be called according to 
the command name, and run them by a command executor which 
is defined as:

.. code-block:: python

    def _execute_custom_handler(
        self:Self,
        handler:Any,
        command:Any,
        client_socket:Any=None,
        client_address:Any=None) -> Any:
        ...

In this excecutor function, there is a try and except code 
block to catch the error when running the command handler. 
If there is an error when running the command handler, the 
server will log the error message and also send the error 
message back to the client if the command is from the client 
side. And in the try code block, the command handler will be 
called with the command arguments, and also the client 
socket and client address if the command is from the client 
side.

If the command don't run in the thread, the command executor 
will be called directly in the `handle_command` function. 
But if the command should run in a separate thread, the command 
executor will be submitted to the server's thread pool using 
the `submit_task` method, which is defined as:

.. code-block:: python

    def submit_task(
        self: Self,
        func: Any,
        *args: Any,
        **kwargs: Any) -> None:
        ...

The `submit_task` method is a helper function that submits 
a callable to the server's internal thread pool executor. 
It accepts a function and its arguments, and schedules it 
for execution in a separate thread. This allows long-running 
or blocking command handlers to run without blocking the 
main server loop.

As a high level TCP network protocal, A temporary TCP server 
and a client can also be created very simply. The temporary 
TCP server or client can be satisfied for the functions which 
need other sockets or ports for avoid to have a conflict with 
the main server or client loop. For example, file transfer 
functions. The APIs to create temporary TCP server and client 
are defined as:

.. code-block:: python

    def create_temporary_server(
        self: Self,
        handler: Any,
        port: Any=None,
        max_connections: Any=1) -> Any:
        ...

    def create_temporary_client(
        self: Self,
        server_host: Any,
        server_port: Any,
        bind_port: Any=None,
        on_data: Any=None) -> Any:
        ...

TCP Server console commands
---------------------------

The server console input thread accepts administrative 
commands when ``is_input_command_in_console`` is ``True``. 
Supported console commands include:

- ``/stop``: stops the server and closes all active connections.
- ``/status``: prints the current connection count and running state.
- ``/clients``: prints the connected clients and their connection times.
- ``/send_msg <message...> <client_id1> <client_id2> ...``: sends one or more messages to specific clients.
- ``/file <file_path> <client_id>``: sends a file from the server to a specific client.
- ``/file_folder <folder_path> <client_id>``: sends a folder from the server to a specific client.
- ``/multiple_file_multiple_client <file1> <file2> ... <client1> <client2> ...``: sends multiple files to multiple clients.
- ``/diff_multiple_file_diff_multiple_client <file1> <file2> ... <client1> <client2> ...``: sends different file lists to different clients.
- ``/help``: prints a help summary of console commands.

These console commands make it easy to manage the 
active server and perform server-initiated file 
transfers without modifying the code.

*Note: There is too long to introduce all the 
commands in the console command list, so for 
more details of the console commands, please 
visit ...*

TCP Server file transfer API
----------------------------

The TCP server contains a file transfer subsystem 
that supports both client-to-server and server-to-client 
transfers.

It's too long to introduce all the file transfer functions, 
so there are only the list of APIs for the file transfer 
functions, and for more detatils of the file transfer 
functions, please visit ...

The file transfer API for you to use includes:

The basic function for the server-to-client 
file transfer is defined as:

.. code-block:: python

    def file_transfer_server_recv_client_start(
        self: Self,
        message: Any,
        file_folder_abspath: Any) -> None|False:
        ...

The file transfer function which will run in 
the threads is defined as:

.. code-block:: python

    def file_transfer_server_recv_client_start_thread(
        self: Self,
        message: Any,
        file_folder_abspath: Any=None) -> None:
        ...

The folder transfer function is defined as:

.. code-block:: python

    def folder_file_transfer_server_recv_client_start(
        self: Self,
        message: Any) -> None|False:
        ...

The multiple files transfer to multiple clients 
function is defined as:

.. code-block:: python

    def multiple_file_multiple_client_transfer_server_recv_client_start(
        self: Self,
        message: Any) -> None|False:
        ...

The different multiple files transfer to the 
different multiple clients function is defined as:

.. code-block:: python

    def diff_multiple_file_diff_multiple_client_transfer_server_recv_client_start(
        self: Self,
        message: Any) -> None|False:
        ...

We recommand you that if you want to use the mono-file 
transfer function, use the `file_transfer_server_recv_client_start_thread` 
function first, unless the functions which called the 
mono-file transfer function are already in a separate 
thread, then you can call the `file_transfer_server_recv_client_start` 
function directly, or the file transfer functions are 
may not very stateble. And for the other file transfer 
functions, we don't very recommand you to use them in 
threads, because there are already some thread control 
mechanisms in the functions, so don't be worry about 
the concurrent performance. And if you call them in 
threads, there may be some unexpected errors and also 
unessarly complexity.

*Note: The file transfer API functions are designed to be 
called from the command handlers for both client-initiated 
and server-initiated transfers. They handle the coordination 
of transfer ports, client connections, and the actual file 
data transfer operations.*

Client-to-server transfer flow:

1. The client sends ``/file`` or ``/file_folder`` to 
   request a transfer.
2. ``handle_command`` starts a dedicated file-server 
   thread using ``file_transfer_server_recv_server_start_thread``.
3. The server allocates an ephemeral transfer port 
   with ``palloc`` and sends 
   ``/server_file_transfer_port <port> <client_id>`` 
   back to the client.
4. The client connects to that transfer port and sends 
   file metadata, including length-prefixed filename 
   and file size.
5. The server receives the file and writes it under 
   ``received_files``.

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

The server allocation APIs allow you to alloc a new 
port for another servers. There are two kinds of port 
allocation modes.

For change the port allocation mode, you can set the 
args ``is_hand_alloc_port`` in the server instence class. 
When input ``False``, the server instence will choose 
the automaticlly port allocation mode, or input ``False`` 
it will choose the manual allocation mode.

We most recommand you that to use the automaticlly port 
allocation mode, which is the default mode of the server, 
because the automaticlly port allocation mode is more 
simple and also more stable than the manual port 
allocation mode. In this mode, when calling the 
allocation APIs, it will return ``0``.

*Note: The `bind` function in standard lib `socket` 
of the python executor, when input ``0`` to the port 
parameter, will automatically assign an available port 
by operating system.*

The another port allocation mode is the manual port 
allocation mode, there is a port allocation range 
for the server. Please avoid to open other servers 
in the same host, because in the existing version, 
the port allocation range will be conflicted and 
some unexpected errors may be caused.

The range of the port allocation is configured in 
the server settings. The minimum allocatable port is 
``self.port-self.port_add_step*self.port_range_num``, 
and the maximum allocatable port is 
``self.port+1+self.port_add_step*self.port_range_num``.

*Note: The ``self.port`` is the args ``port`` of the 
server class. The ``self.port_add_step`` is the args 
``port_add_step`` of the server class. And the 
``self.port_range_num`` is the args ``port_range_num`` 
of the server class also.*

There are some relevant methods that can be used:

.. code-block:: python

    def palloc(self: Self) -> int:
        ...

The `palloc` method allow you to get a port, for 
using this function, you don't need to worry about 
the port allocation mode, because a allocation mode 
detector is already be wrote in this method.

.. code-block:: python

    def pfree(
        self: Self,
        port: int) -> None|int:
        ...

The `pfree` method allow you to free a port, as the same 
as `palloc` method, you don't need to care about the 
port allocation mode when using this method.

And there are the main functions for you to call, and 
for more informations about the port allocation functions, 
please visit ...

This mode is useful when you need a indvidual port for 
the server or  must reserve a controlled range of ports 
for client-file transfers by manual port allocation, 
such as in a testing environment or when multiple 
server processes share the same host.

TCP Server APIs table
----------------------

In short, the table of contents of the public APIs 
are following as:

1. The server setup APIs:
    - `TCP_Server_Base`
    - `start_TCP_Server`
    - `stop`

2. The server handling information APIs:
    - `handle_client`
    - `handle_command`
    - `recieve_message`
    - `send_message`
    - `broadcast`
    - `send_msg_to_specific_client`

3. The server command APIs:
    - `register_command`
    - `_execute_custom_handler`
    - `submit_task`
    - `create_temporary_server`
    - `create_temporary_client`

4. The server file transfer APIs:
    - `file_transfer_server_recv_client_start`
    - `file_transfer_server_recv_client_start_thread`
    - `folder_file_transfer_server_recv_client_start`
    - `multiple_file_multiple_client_transfer_server_recv_client_start`
    - `diff_multiple_file_diff_multiple_client_transfer_server_recv_client_start`

5. The server console commands:
    - `/stop`
    - `/status`
    - `/clients`
    - `/send_msg`
    - `/file`
    - `/file_folder`
    - `/multiple_file_multiple_client`
    - `/diff_multiple_file_diff_multiple_client`
    - `/help`

See Also
--------

For more informations about the client APIs, 
please visit the client API documentation, at 
:doc:`TCP_Client_APIs`.

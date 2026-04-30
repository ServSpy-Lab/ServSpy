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
    self.clients[client_address: ] = {
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

    def handle_client(self, client_socket, client_address):
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
and ``is_hand_alloc_port``. And for more information, 
please visit ...*

- receiving raw bytes from the socket using ``recieve_message``
- buffering incoming data until newline-terminated messages are complete
- splitting and processing each message line-by-line
- routing special commands beginning with ``/`` to ``handle_command``
- logging normal chat messages and acknowledging receipt
- removing the client from ``self.clients`` and closing the socket when the client disconnects or an error occurs

.. code-block:: python

    def recieve_message(self, client_socket, msg_length):
        ...

`recieve_message` is a thin wrapper around socket receive operations. 
It reads up to ``msg_length`` bytes from the given 
``client_socket`` and returns the raw byte payload. 
Message decoding and newline message framing are handled 
by the caller.

.. code-block:: python

    def send_message(self, client_socket, message):
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

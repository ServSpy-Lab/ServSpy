TCP File Transfer Mechanism
===========================

This document describes the file transfer subsystem
implemented in both the
``TCP_Server_Base`` and ``TCP_Client_Base`` classes. The
file transfer mechanism
allows sending and receiving single files, folders,
multiple files, and multiple
folders between a server and its connected clients. It
also supports
server-initiated transfers from the server console.

The design follows a **two-phase handshake** pattern:

1. A transfer command is exchanged over the main
   control connection.
2. A separate TCP connection is established on a
   dynamically allocated port to
   transfer the actual file data (metadata + payload).

All file transfers use **stream-oriented reading/writing**
with fixed-size chunks
(by default 64 KiB) to avoid blocking and to handle large
files efficiently.

*Note: For a high-level overview of the server and client
classes, please refer to
:doc:`TCP_Server_APIs` and :doc:`TCP_Client_APIs`.*

.. _file-transfer-protocol:

File Transfer Protocol
----------------------

The protocol is symmetric: the same low-level exchange is
used regardless of
whether the server sends to a client or the client sends
to the server. The
**initiator** of the transfer (the side that sends the
command) also acts as the
**sender** of the file data; the other side acts as the
**receiver**.

The protocol uses a set of predefined string constants,
loaded from
``decode_command_table.json``:

- ``server_start_file_transfer_sign`` - sent by the
  receiver to the sender,
  indicating that the receiver is ready.
- ``server_reseived_file_header_sign`` - sent by the
  receiver after it has
  successfully read the filename and file size.
- ``server_reseived_file_data_sign`` - sent by the
  receiver after the complete
  file has been written to disk.
- ``error_sign`` - sent by either side when an error
  occurs, causing the
  transfer socket to be closed.

### Metadata Exchange

The sender performs the following steps after the
dedicated file-transfer socket
is connected:

- Wait for the receiver's start signal
  (``server_start_file_transfer_sign``)
  with a 10-second timeout.
- Send the filename length as a 4-byte unsigned integer
  (big-endian).
- Send the filename encoded in UTF-8.
- Send the file size as an 8-byte unsigned integer
  (big-endian).
- Send the file content in 64 KiB chunks until EOF.
- Wait for the completion acknowledgement
  (``server_reseived_file_data_sign``) with a dynamic
  timeout (base 30 seconds
  plus 10 seconds per 100 MiB).

The receiver performs the complementary steps:

- Send the start signal.
- Read the 4-byte length, then the filename, then the
  8-byte size.
- Acknowledge the header with
  ``server_reseived_file_header_sign``.
- Receive the file data in chunks and write to disk.
- Acknowledge completion with
  ``server_reseived_file_data_sign``.

Any error during the exchange causes the failing side to
send ``error_sign``,
and both sides close the transfer socket. The main control
connection remains
unaffected.

.. _client-initiated-flow:

Client-Initiated Transfer (Client → Server)
--------------------------------------------

When the user types a file-related command in the client's
interactive console,
the call chain proceeds as follows.

### Console Input Handling

In ``TCP_Client_Base.interactive_mode()``, user input is
read line by line.
Commands starting with ``/file``, ``/multiple_file``,
``/file_folder``, or
``/multiple_file_folder`` are recognised. For each such
command, the client
calls the corresponding thread-safe entry point (the
methods ending with
``_thread``).

### Thread-Safe Entry Points

The client provides the following thread-safe methods for
initiating transfers:

- ``file_transfer_client_recv_client_start_thread(message,
  file_folder_abspath=None)``
- ``folder_file_transfer_client_recv_client_start(message)``
- ``multiple_file_transfer_client_recv_client_start(message)``
- ``multiple_folder_file_transfer_client_recv_client_start(message)``

Each of these methods creates a new daemon thread that
executes the actual
worker function (the non-``_thread`` version). This
prevents the console thread
from being blocked.

### Worker Function (Client Side)

The core worker function for a single file is
``file_transfer_client_recv_client_start(message,
file_folder_abspath=None)``.
Its logic is as follows:

1. Allocate a unique client ID using the lock
   ``file_client_id_lock``.
2. Extend the original command string with the client
   ID (e.g.,
   ``/file mydoc.txt`` becomes ``/file mydoc.txt 42``)
   and send it to the server
   over the main control connection using
   ``send_message()``.
3. Obtain a local port for the outgoing file transfer
   socket by calling
   ``palloc()``.
4. Wait (up to 20 seconds) for the server to reply with
   a port number. The
   server's reply (``/server_file_transfer_port <port>
   <client_id>``) is
   received by the main connection and stored in
   ``file_server_port_list``.
   When a matching entry is found, the port is
   extracted.
5. Call the low-level send function
   ``file_transfer_mode(filename, server_host,
   server_port, client_port)``.

For folder transfers, the worker function
``folder_file_transfer_client_recv_client_start(message)``
recursively walks the
directory tree. For each subdirectory (except the top
level), it sends a
``/file_folder <relative_path>`` command over the main
connection to create the
corresponding directory on the server. For each file, it
calls
``file_transfer_client_recv_client_start_thread`` with a
command of the form
``/file_folder <relative_path> <file_name>``. A semaphore
(``file_semaphore``) limits the number of concurrent file
transfers to
``max_thread_num``.

### Server-Side Handler (Receiving)

When the server receives an extended command like ``/file
mydoc.txt 42`` on the
main control connection, ``handle_command`` detects it and
calls:

- ``file_transfer_server_recv_server_start_thread(client_id,
  client_socket, command)``

The server then:

1. Creates a new thread via
   ``file_transfer_server_recv_server_start(client_id,
   client_socket, command,
   new_save_path=None, file_name=None)``.
2. Allocates a transfer port with ``palloc()``.
3. Calls ``file_transfer_mode_recv(host, port,
   client_socket, client_id,
   new_save_path, file_name, command)``.
4. This low-level receive function sets up a listening
   socket on the allocated
   port, sends the port number back to the client (as
   ``/server_file_transfer_port <port> <client_id>``),
   accepts the client's
   connection, and performs the protocol steps
   described in
   :ref:`file-transfer-protocol`. The received file is saved under
   ``received_files/`` (or a subdirectory if a folder
   transfer was requested).
5. After the transfer completes (or fails), the port is
   released with
   ``pfree()``.

.. _server-initiated-flow:

Server-Initiated Transfer (Server → Client)
--------------------------------------------

When the server administrator types a command in the
server console, for example
``/file /path/to/file.txt (127.0.0.1,54321)``, the console
input thread
(``console_input``) parses the command and calls the
appropriate server-side
file transfer API.

The recommended entry points for server-to-client
transfers are:

- ``file_transfer_server_recv_client_start_thread(message,
  file_folder_abspath=None)``
  for a single file.
- ``folder_file_transfer_server_recv_client_start(message)``
  for a folder.
- ``multiple_file_multiple_client_transfer_server_recv_client_start(message)``
  for multiple files to multiple clients.
- ``diff_multiple_file_diff_multiple_client_transfer_server_recv_client_start(message)``
  for different file lists to different clients.

The worker function
``file_transfer_server_recv_client_start(message,
file_folder_abspath=None)``
performs the following steps:

1. Extract the target client address from the last part
   of the command (e.g.,
   ``(127.0.0.1,54321)``) using ``ast.literal_eval()``.
   Obtain the client's
   socket from ``self.clients``.
2. Allocate a unique client ID and extend the command
   with it, then send the
   extended command to the client over the main
   connection.
3. Allocate a local port with ``palloc()``.
4. Wait for the client to reply with its own port
   number (via
   ``/server_file_transfer_port``), which is stored in
   ``file_server_port_list``
   by the main connection's message handler.
5. Call ``file_transfer_mode(filename, client_host,
   client_port, local_port)``
   to send the file.

On the client side, when it receives a command like
``/file /path/to/file.txt (127.0.0.1,54321) 42``,
``handle_server_command`` calls
``file_transfer_client_recv_server_start_thread(client_id,
client_socket, command)``.
This starts a receiver thread analogous to the server's
receiver for
client-initiated transfers: it allocates a port, replies
with
``/server_file_transfer_port``, and calls
``file_transfer_mode_recv`` to receive
and save the file.

.. _folder-transfer-mechanism:

Folder Transfer Mechanism (Detailed)
-------------------------------------

Transferring a folder is implemented as a **recursive
walk** that sends separate
commands for subdirectories and files. The logic is
symmetric on both client and
server.

### Creating Directories

For a directory that needs to be created on the receiver
side, the sender sends
a command of the form:

``/file_folder <relative_path>``

The receiver's handler for this command (in either
``file_folder_transfer_server_recv_server_start_thread``
or
``file_folder_transfer_client_recv_server_start_thread``)
creates the
corresponding directory under the base receive directory
(``received_files/`` for the server, the same directory
for the client). The
relative path uses forward slashes to be
platform-independent.

### Sending Files Inside a Folder

For each file, the sender sends a command of the form:

``/file_folder <relative_path> <file_name>``

The receiver treats this as a file transfer request. The
second argument
(``file_name``) is used as the final filename, and the
relative path determines
the subdirectory under the base receive directory. The
actual file data is
transferred using the same single-file protocol (via
``file_transfer_client_recv_client_start`` or
``file_transfer_server_recv_client_start``, depending on
direction).

### Concurrency Control for Folders

Because a folder can contain many files, the sender uses a
semaphore
(``file_semaphore``) to limit the number of concurrently
active file transfers.
The semaphore is acquired before starting each file
transfer and released in a
``finally`` block. The maximum concurrency is set by
``max_thread_num`` on the
client and ``max_file_transfer_thread_num`` on the server.

.. _concurrency-and-threading:

Concurrency and Threading
-------------------------

Both the server and the client use multiple levels of
concurrency control to
ensure stability during file transfers.

### File Transfer Semaphore

- Client: ``self.file_semaphore =
  threading.Semaphore(max_thread_num)``
- Server: ``self.file_semaphore =
  threading.Semaphore(max_file_transfer_thread_num)``

This semaphore limits the number of simultaneous file
transfers (used primarily
when sending folders or multiple files). Each transfer
runs in its own thread,
and the semaphore is acquired before the thread is
started.

### Threading Model

- Each file transfer runs in a dedicated daemon thread,
  created by the
  ``_thread`` wrapper functions (e.g.,
  ``file_transfer_client_recv_client_start_thread``).
  This prevents a slow
  transfer from blocking the main control loop.
- The thread that receives the transfer command (e.g.,
  the server's
  ``handle_command`` thread) does not wait for the
  transfer to complete; it
  returns immediately after spawning the worker thread.
- The low-level receive function
  (``file_transfer_mode_recv``) blocks while
  reading from the transfer socket, but because it runs
  in a dedicated thread,
  the main connection remains responsive.

### Thread Pool for Custom Commands

Both classes also provide a ``ThreadPoolExecutor``
(``self._custom_executor``)
for custom command handlers. When a handler is registered
with
``run_in_thread=True``, it is submitted to this pool via
``submit_task``, which
also uses a semaphore to limit concurrency to
``max_custom_workers``. This
mechanism is **independent** of the file transfer
semaphore and is intended for
general-purpose command processing.

.. _port-allocation:

Port Allocation and Management
------------------------------

File transfers require ephemeral ports for the secondary
data connections. The
``palloc()`` and ``pfree()`` methods are used to obtain
and release these ports.
Two modes are available:

- **Automatic mode** (``is_hand_alloc_port=False``):
  ``palloc()`` returns ``0``,
  and the operating system assigns a free port when the
  socket is bound. This is
  the recommended mode for most use cases.
- **Manual mode** (``is_hand_alloc_port=True``): Ports
  are drawn from a
  configurable range ``[self.min_port, self.max_port]``
  with a step size
  ``port_add_step``. The server broadcasts the allowed
  range to clients via
  ``/client_alloc_port_range``, and clients then use the
  same manual allocation
  logic.

*Note: For more details about port allocation, please
visit the Port Allocation API
sections in :doc:`TCP_Server_APIs` and
:doc:`TCP_Client_APIs`.*

.. _error-handling:

Error Handling and Timeouts
---------------------------

### Timeout Values

- **Start signal timeout**: 10 seconds. If the receiver
  does not send
  ``server_start_file_transfer_sign`` within this time,
  the sender aborts.
- **Port negotiation timeout**: 20 seconds. The
  initiator waits for the peer's
  ``/server_file_transfer_port`` response.
- **Completion acknowledgement timeout**: ``30 +
  (file_size // (100 * 1024 * 1024)) * 10``
  seconds. Larger files get proportionally more time.

### Error Signalling

- Any error during the handshake or data transfer causes
  the failing side to
  send ``error_sign`` over the transfer socket.
- The other side, upon receiving the error sign, closes
  the transfer socket and
  aborts the transfer.
- The main control connection remains unaffected; only
  the transfer socket is
  closed.

### Exception Handling

All socket operations are wrapped in try-except blocks.
When an exception occurs
(e.g., connection reset, file not found), the error is
logged with
``traceback.print_exc()`` and the transfer is aborted
gracefully. The
``error_sign`` is sent if possible, and the transfer
socket is closed.

.. _related-apis:

Related API Definitions
-----------------------

This section lists all public file-transfer related
methods in
``TCP_Server_Base`` and ``TCP_Client_Base``. For a
complete list of all public
APIs, please see the tables at the end of this document.

### Server-Side File Transfer APIs

.. code-block:: python

    def file_transfer_server_recv_client_start(
        self,
        message: str,
        file_folder_abspath: str = None
    ) -> None | False

Initiates a server-to-client file transfer. ``message`` is the command string
(e.g., ``/file /path/to/file.txt (127.0.0.1,54321)``). If
``file_folder_abspath``
is provided (for folder transfers), it specifies the
absolute path of the parent
folder.

.. code-block:: python

    def file_transfer_server_recv_client_start_thread(
        self,
        message: str,
        file_folder_abspath: str = None
    ) -> None

Thread-safe version that starts a new thread for the transfer.

.. code-block:: python

    def folder_file_transfer_server_recv_client_start(
        self,
        message: str
    ) -> None | False

Sends an entire folder from server to client. ``message`` should be of the form
``/file_folder <folder_path> <client_address>``.

.. code-block:: python

    def multiple_file_multiple_client_transfer_server_recv_client_start(
        self,
        message: str
    ) -> None

Sends multiple files to multiple clients. The message format is
``/multiple_file_multiple_client <file1> <file2> ...
<client_addr1> <client_addr2> ...``.
Files must appear before clients.

.. code-block:: python

    def diff_multiple_file_diff_multiple_client_transfer_server_recv_client_start(
        self,
        message: str
    ) -> None

Sends different file lists to different clients. The message alternates between
groups: a list of files, then a list of client addresses,
then the next list of
files, etc. Example:
``/diff_multiple_file_diff_multiple_client a.txt b.txt
(ip1,port1) (ip2,port2) c.txt (ip3,port3)``

.. code-block:: python

    def file_transfer_server_recv_server_start(
        self,
        client_id: str,
        client_socket: socket.socket,
        command: str,
        new_save_path: str = None,
        file_name: str = None
    ) -> None

Receives a file from a client. Called internally when the server receives a
``/file`` command from a client.

.. code-block:: python

    def file_transfer_mode_recv(
        self,
        server_file_address: str,
        server_file_port: int,
        client_socket: socket.socket,
        client_id: str,
        new_save_path: str,
        file_name: str,
        command: str
    ) -> None

Low-level receive function that performs the handshake and writes the incoming
file to disk.

.. code-block:: python

    def file_transfer_mode(
        self,
        filename: str,
        server_address: str,
        server_port: int,
        client_port: int
    ) -> bool

Low-level send function that connects to the receiver and transmits the file.

### Client-Side File Transfer APIs

.. code-block:: python

    def file_transfer_client_recv_client_start(
        self,
        message: str,
        file_folder_abspath: str = None
    ) -> None | False

Initiates a client-to-server file transfer. ``message`` is the user command
(e.g., ``/file mydoc.txt``). Used internally by the
interactive console.

.. code-block:: python

    def file_transfer_client_recv_client_start_thread(
        self,
        message: str,
        file_folder_abspath: str = None
    ) -> None

Thread-safe version.

.. code-block:: python

    def folder_file_transfer_client_recv_client_start(
        self,
        message: str
    ) -> None | False

Sends a folder from client to server.

.. code-block:: python

    def multiple_file_transfer_client_recv_client_start(
        self,
        message: str
    ) -> None

Sends multiple files from client to server.

.. code-block:: python

    def multiple_folder_file_transfer_client_recv_client_start(
        self,
        message: str
    ) -> None

Sends multiple folders from client to server.

.. code-block:: python

    def file_transfer_client_recv_server_start(
        self,
        client_id: str,
        client_socket: socket.socket,
        command: str,
        new_save_path: str = None,
        file_name: str = None
    ) -> None

Receives a file from the server (called when the server initiates a transfer).

.. code-block:: python

    def file_transfer_client_recv_server_start_thread(
        self,
        client_id: str,
        client_socket: socket.socket,
        command: str
    ) -> None

Thread-safe version.

.. code-block:: python

    def file_folder_transfer_client_recv_server_start_thread(
        self,
        command: str,
        client_id: str,
        client_socket: socket.socket
    ) -> None

Receives a folder from the server.

.. code-block:: python

    def file_transfer_mode_recv(
        self,
        server_file_address: str,
        server_file_port: int,
        client_socket: socket.socket,
        client_id: str,
        new_save_path: str,
        file_name: str,
        command: str
    ) -> None

Low-level receive function on the client side.

.. code-block:: python

    def file_transfer_mode(
        self,
        filename: str,
        server_address: str,
        server_port: int,
        client_port: int
    ) -> bool

Low‑level send function on the client side (identical to server's version).

.. _public-api-summary:

Public API Summary
------------------

All public APIs (including non-file-transfer methods) are
listed below for
reference.

### TCP_Server_Base Public APIs

- ``file_transfer_server_recv_client_start``
- ``file_transfer_server_recv_client_start_thread``
- ``folder_file_transfer_server_recv_client_start``
- ``multiple_file_multiple_client_transfer_server_recv_client_start``
- ``diff_multiple_file_diff_multiple_client_transfer_server_recv_client_start``

(The low-level helpers
``file_transfer_server_recv_server_start``,
``file_transfer_mode_recv``, and ``file_transfer_mode``
are not considered
public but are documented for completeness.)

### TCP_Client_Base Public APIs

- ``file_transfer_client_recv_client_start``
- ``file_transfer_client_recv_client_start_thread``
- ``folder_file_transfer_client_recv_client_start``
- ``multiple_file_transfer_client_recv_client_start``
- ``multiple_folder_file_transfer_client_recv_client_start``
- ``file_transfer_client_recv_server_start``
- ``file_transfer_client_recv_server_start_thread``
- ``file_folder_transfer_client_recv_server_start_thread``

(The low-level helpers are documented but not part of the
public API.)

See Also
--------

For more information about the TCP server and client base
classes, please refer
to:

- :doc:`../Network_APIs/TCP_Server_APIs`
- :doc:`../Network_APIs/TCP_Client_APIs`

For details on port allocation, see the Port Allocation
API sections in those
documents.

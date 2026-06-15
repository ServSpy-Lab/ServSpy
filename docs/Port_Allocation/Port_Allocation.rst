TCP Port Allocation Mechanism
==============================

This document describes the port allocation subsystem
implemented in both the
``TCP_Server_Base`` and ``TCP_Client_Base`` classes. The
port allocation
mechanism provides a unified interface for obtaining
ephemeral ports, supporting
both **automatic** (OS‑assigned) and **manual**
(range‑based) allocation modes.

Port allocation is used primarily for file transfer
secondary connections,
temporary servers, and temporary clients. The design
ensures that ports are
allocated and released without conflicts, even when
multiple server or client
instances run on the same host.

For a high‑level overview of the server and client
classes, please refer to
:doc:`../Network_APIs/TCP_Server_APIs` and :doc:`../Network_APIs/TCP_Client_APIs`.

.. _port-allocation-overview:

Overview
--------

The port allocation API consists of two core methods:

- ``palloc()`` – obtain an available port.
- ``pfree(port)`` – release a previously allocated port.

The behaviour of these methods depends on the value of the
``is_hand_alloc_port`` flag passed to the class
constructor:

- **Automatic mode** (``is_hand_alloc_port=False``,
  default): ``palloc()``
  returns ``0``. When used in a socket ``bind()`` call,
  the operating system
  automatically assigns a free ephemeral port.
  ``pfree()`` does nothing.
- **Manual mode** (``is_hand_alloc_port=True``): Ports
  are drawn from a
  configurable numeric range. The caller must eventually
  release each allocated
  port with ``pfree()``.

Automatic mode is strongly recommended for most
applications because it avoids
port conflicts and simplifies code. Manual mode is
provided for environments
where port ranges must be strictly controlled (e.g.,
firewalls, testing, or
multiple processes sharing the same host).

.. _manual-allocation-range:

Manual Allocation Range
-----------------------

When manual mode is enabled, the allocatable port range is
determined by three
parameters set during class initialisation:

- ``port`` – the main server or client port (e.g.,
  65432).
- ``port_add_step`` – the step size for
  incrementing/decrementing ports.
- ``port_range_num`` – the total number of steps to scan
  in each direction.

From these, the minimum and maximum allocatable ports are
calculated as:

- ``min_port = port - port_add_step * port_range_num``
- ``max_port = port + 1 + port_add_step *
  port_range_num``

For example, with ``port=65432``, ``port_add_step=1``,
``port_range_num=100``,
the allocatable ports range from ``65432 - 100 = 64332``
up to
``65432 + 1 + 100 = 65533``.

Two independent allocation “directions” are maintained:

- **Additive allocation** – starts from ``port+1`` and
  moves upward by
  ``port_add_step`` each time, up to (but not including)
  ``max_port``.
- **Subtractive allocation** – starts from ``port`` and
  moves downward by
  ``port_add_step`` each time, down to (but not
  including) ``min_port``.

The two directions use separate locks and separate current
position pointers,
allowing two concurrent allocations to proceed in opposite
directions without
colliding, thereby reducing contention.

.. _palloc-behaviour:

palloc() Behaviour in Manual Mode
---------------------------------

When ``palloc()`` is called in manual mode, it first tries
additive allocation.
If additive allocation returns a port, that port is
returned immediately.
Otherwise, it tries subtractive allocation. If subtractive
allocation also fails
(meaning no ports are available in either direction), the
method sleeps for 0.1
seconds and then retries from the beginning. This loop
continues indefinitely
until a port becomes free.

Additive allocation works as follows:

- If the next additive step would exceed the maximum
  allowed value, the
  allocator scans all remaining ports in the additive
  direction (starting from
  ``port+1``, stepping by ``port_add_step``, up to but
  not including
  ``max_port``). The first port that is not already in
  the global allocated list
  is returned. If none is found, additive allocation
  fails.
- Otherwise, the additive pointer is advanced by
  ``port_add_step``, the new port
  is added to the global allocated list, and the port is
  returned.

Subtractive allocation works symmetrically, scanning
downward from ``port`` to
(but not including) ``min_port``.

.. _pfree-behaviour:

pfree() Behaviour in Manual Mode
--------------------------------

When a port is released via ``pfree(port)``:

- The port is removed from the global allocated list (if
  present).
- The additive pointer is **decremented** by
  ``port_add_step``.
- The subtractive pointer is **incremented** by
  ``port_add_step``.

These pointer adjustments occur regardless of which
direction originally
allocated the port. This allows freed ports to be reused
in future allocations.

.. _persistence-and-file-locks:

Persistence and File Locks (Manual Mode Only)
----------------------------------------------

When manual mode is enabled, the server or client must
remember allocated port
ranges across multiple instances to avoid conflicts. This
is achieved through
persistent log files stored in the ``.ServSpy/temp_info/``
directory.

- **Server**: ``server_port_info.log`` stores a list of
  dictionaries, each
  describing a server instance (server_id, host, port,
  min_port, max_port,
  is_running).
- **Client**: ``clients_port_info.log`` stores similar
  information for client
  instances.

Before reading or writing these files, a lock file
(``server_port_lock.lock`` or
``client_port_lock.lock``) is used to prevent concurrent
access. The lock is
implemented by simply creating the file; the existence of
the file indicates
that another process is currently modifying the port
information.

When a new server or client instance is created with
manual allocation enabled,
its range is initialised using the persistent log:

- If the log file does not exist, a new list is created
  with the current
  instance as the first entry.
- If the log file exists, the list of previous instances
  is read. The next
  instance ID is the previous ID + 1.
- If the user‑supplied port falls inside the range of
  the last recorded
  instance, it is automatically advanced to the next
  available value to prevent
  overlap.
- The new instance’s information is appended to the
  list, stale entries
  (``is_running=False``) are removed, and the list is
  written back.

When the server or client stops, its own entry is removed
from the log file. If
the list becomes empty, the log file is deleted.

.. _client-range-configuration:

Client‑Side Range Configuration
-------------------------------

The client’s manual allocation mode is enabled not by a
constructor argument
directly, but by a **broadcast from the server**. When the
server starts with
``is_hand_alloc_port=True``, it sends a command to all
clients:

``/client_alloc_port_range <each_client_port_range>``

where ``each_client_port_range = port_range_num //
max_clients``.

The client’s ``handle_server_command`` processes this:

- If the value is ``"NO_LIMIT"``, the client sets
  ``is_hand_alloc_port=False``
  (automatic mode).
- Otherwise, it sets ``is_hand_alloc_port=True`` and
  calls its internal
  initialisation routine with the received range, using
  its own ``port`` (the
  server port it connected to) as the base.

This allows the server to control the port‑allocation
policy for all connected
clients uniformly.

.. _api-definitions:

Public API Definitions
----------------------

### Server‑Side Port Allocation APIs

.. code-block:: python

    def palloc(self) -> int

Returns an available port number. In automatic mode,
returns ``0``. In manual mode, it returns a concrete
port from the configured range, retrying indefinitely
until a port becomes available.

.. code-block:: python

    def pfree(self, port: int) -> None

Releases a port previously obtained by ``palloc()``.
In automatic mode, this does nothing. In manual mode,
it removes the port from the internal allocated list
and adjusts the allocation pointers.

### Client‑Side Port Allocation APIs

The client provides the identical set of methods:

- ``palloc()``
- ``pfree(port)``

Additionally, the client receives the range from the
server via the
``/client_alloc_port_range`` command.

.. _public-api-summary:

Public API Summary
-------------------

All public port‑allocation related APIs are listed below.
For a complete list
of all public APIs, please see the respective server and
client documentation.

### TCP_Server_Base

- ``palloc``
- ``pfree``

### TCP_Client_Base

- ``palloc``
- ``pfree``

See Also
--------

For more information about the TCP server and client base
classes, please refer
to:

- :doc:`../Network_APIs/TCP_Server_APIs`
- :doc:`../Network_APIs/TCP_Client_APIs`

For details on the file transfer mechanism that uses these
port allocation APIs,
see :doc:`../File_Transfer/File_Transfer`.

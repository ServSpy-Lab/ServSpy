UDP API
=======

A lightweight UDP endpoint for service discovery, broadcast, and
simple request-response communication.

.. code-block:: python

    class UDP:
        def __init__(self, host="0.0.0.0", port=0):
            ...

The socket is created and bound in the constructor.
Both ``SO_REUSEADDR`` and ``SO_BROADCAST`` are set automatically.

Parameters
----------

- ``host``: Interface to bind to. Default ``"0.0.0.0"`` (all interfaces).
- ``port``: Port to bind to. ``0`` lets the OS choose.

Properties
----------

.. code-block:: python

    @property
    def port(self) -> int
    @property
    def local_addr(self) -> tuple[str, int]

Methods
-------

.. code-block:: python

    def send(self, data: bytes, addr: tuple) -> None
    def broadcast(self, data: bytes, port: int) -> None
    def listen(self, handler) -> None
    def close(self) -> None

``send(data, addr)``
    Send a datagram. Raises ``OSError`` on network failure.

``broadcast(data, port)``
    Broadcast a datagram to the subnet.

``listen(handler)``
    Start receiving datagrams in a daemon thread. Calls
    ``handler(data, addr)`` for each incoming datagram until
    ``close()`` is called. Handler exceptions are logged, not
    raised. Idempotent.

``close()``
    Signal the receive loop to exit and close the socket. Idempotent.

``UDP`` supports the ``with`` statement: ``with UDP(...) as u: ...``

Usage patterns
--------------

Echo server::

    from src.connect_udp import UDP

    s = UDP("127.0.0.1", 65000)
    s.listen(lambda data, addr: s.send(data, addr))
    # Ctrl+C to exit

Client with reply (using raw socket for synchronous receive)::

    import socket
    from src.connect_udp import UDP

    srv = UDP("127.0.0.1", 65000)
    srv.listen(lambda data, addr: srv.send(b"pong", addr))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.sendto(b"/ping", ("127.0.0.1", 65000))
    sock.settimeout(2)
    try:
        data, addr = sock.recvfrom(65535)
        print(data.decode())  # "pong"
    except TimeoutError:
        print("no reply")
    finally:
        sock.close()
    srv.close()

Broadcast discovery::

    from src.connect_udp import UDP

    srv = UDP("0.0.0.0", 65000)
    srv.listen(lambda data, addr: print(f"recv from {addr}: {data.decode()}"))

    c = UDP()
    c.broadcast(b"/who", 65000)
    c.close()
    srv.close()

Blocking mode (user-managed thread)::

    import threading
    from src.connect_udp import UDP

    s = UDP("127.0.0.1", 65000)
    s.listen(lambda d, a: print(d))
    # thread runs until close()
    s.close()

Key differences from TCP
------------------------

- **No file transfer**. UDP is unreliable; use TCP classes for file transfers.
- **No connection tracking**. Each datagram carries its own source address.
- **No port allocation system**. UDP does not need ephemeral ports for
  data connections.
- **Broadcast**. UDP's standout feature — one send reaches all listeners
  on the subnet.

See Also
--------

- :doc:`TCP_Server_APIs` — TCP server.
- :doc:`TCP_Client_APIs` — TCP client.

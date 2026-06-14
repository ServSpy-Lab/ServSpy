import socket
import threading

import pytest

from src.connect_udp import UDP

UDP_BROADCAST_PORT = 65030


def test_udp_server_init(udp_server):
    assert udp_server.port > 0


def test_udp_client_init(udp_client):
    assert udp_client.port > 0
    host, port = udp_client.local_addr
    assert host == "127.0.0.1"
    assert port == udp_client.port


def test_udp_create_and_close():
    udp = UDP("127.0.0.1", 0)
    assert udp._socket.fileno() >= 0
    udp.close()
    assert udp._socket.fileno() == -1


def test_udp_send_and_reply():
    server = UDP("127.0.0.1", 0)

    def on_msg(data, addr):
        if data.strip() == b"/ping":
            server.send(b"pong", addr)

    server.listen(on_msg)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    try:
        sock.sendto(b"/ping", ("127.0.0.1", server.port))
        sock.settimeout(2)
        data, addr = sock.recvfrom(65535)
        assert data.strip() == b"pong"
    finally:
        sock.close()
        server.close()


def test_udp_broadcast():
    received = threading.Event()

    s1 = UDP("0.0.0.0", UDP_BROADCAST_PORT)
    s1.listen(lambda data, addr: received.set())

    c = UDP("0.0.0.0")
    try:
        c.broadcast(b"/probe", UDP_BROADCAST_PORT)
        assert received.wait(timeout=2), "did not receive broadcast"
    finally:
        c.close()
        s1.close()


def test_udp_noop_handler_does_not_write_to_stdout(udp_server, capsys):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(b"/nonexistent", ("127.0.0.1", udp_server.port))
    sock.close()

    captured = capsys.readouterr()
    assert captured.out == ""


def test_udp_send_rejects_closed():
    udp = UDP("127.0.0.1", 0)
    udp.close()
    with pytest.raises(OSError):
        udp.send(b"data", ("127.0.0.1", 9999))


def test_udp_close_stops_recv_loop():
    udp = UDP("127.0.0.1", 0)
    udp.listen(lambda data, addr: None)
    assert udp._recv_thread.is_alive()
    udp.close()
    assert udp._socket.fileno() == -1


def test_udp_callback_exception_does_not_kill_loop():
    udp = UDP("127.0.0.1", 0)
    received = threading.Event()

    def faulty_cb(data, addr):
        try:
            raise ValueError("simulated error")
        finally:
            received.set()

    udp.listen(faulty_cb)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b"data", ("127.0.0.1", udp.port))
        sock.close()

        assert received.wait(timeout=1), "callback was never called"
        assert udp._recv_thread.is_alive()
    finally:
        udp.close()


def test_udp_close_idempotent():
    udp = UDP("127.0.0.1", 0)
    udp.close()
    udp.close()


def test_udp_listen_after_close():
    udp = UDP("127.0.0.1", 0)
    udp.close()
    with pytest.raises(RuntimeError, match="endpoint is closed"):
        udp.listen(lambda data, addr: None)


def test_udp_context_manager():
    with UDP("127.0.0.1", 0) as udp:
        assert udp._socket.fileno() >= 0
    assert udp._socket.fileno() == -1


def test_udp_listen_idempotent():
    udp = UDP("127.0.0.1", 0)
    udp.listen(lambda data, addr: None)
    thread = udp._recv_thread
    udp.listen(lambda data, addr: None)
    assert udp._recv_thread is thread
    udp.close()


def test_udp_listen_stops_on_close():
    udp = UDP("127.0.0.1", 0)
    received = threading.Event()

    udp.listen(lambda data, addr: received.set())

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(b"hello", ("127.0.0.1", udp.port))
    sock.close()

    assert received.wait(timeout=2), "handler was not called"

    thread = udp._recv_thread
    udp.close()
    thread.join(timeout=1)
    assert not thread.is_alive()

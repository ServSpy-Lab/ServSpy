import os
import sys
import uuid
import shlex
import logging
import subprocess
import threading
import time
import ast
from . import connect_tcp
from datetime import datetime

server_instance=None
client_instance=None

def _setup_command():
    print("Setting up server command...")
    server_instance.register_command(
        command_name="/test_command", handler=_command_handler,
        where_to_run="client", run_in_thread=False)

def _command_handler(sock, addr, cmd):
    print(f"Received command from {addr}: {cmd}")
    print(server_instance.clients)
    return "Command received."

def client_setup():
    global client_instance
    client_instance=connect_tcp.TCP_Client_Base(
        host='127.0.0.1', port=65432,
        client_host='127.0.0.1', is_input_command_in_console=True, is_extend_command=True)
    client_instance.start_TCP_client()

def server_setup():
    global server_instance
    server_instance=connect_tcp.TCP_Server_Base(
        host='127.0.0.1', port=65432, max_clients=10,
        is_input_command_in_console=True, is_extend_command=True)
    _setup_command()
    server_instance.start_TCP_Server()

# threading.Thread(target=server_setup, daemon=True).start()
# print("Server is starting...")
# time.sleep(1)  # 等待服务器启动
# threading.Thread(target=client_setup, daemon=True).start()
# print("Client is starting...")

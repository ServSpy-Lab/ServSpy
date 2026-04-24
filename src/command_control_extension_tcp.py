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
        command_name="/command", handler=_command_handler,
        where_to_run="client", run_in_thread=True)
    
def _setup_client_command():
    print("Setting up client command...")
    client_instance.register_command(
        command_name="/command", handler=_command_handler_server_setup,
        where_to_run="server", run_in_thread=True)

def _command_handler(sock, addr, cmd):
    print(f"Received command from {addr}: {cmd}")
    client_class=server_instance.clients
    cmd_part=shlex.split(cmd)
    del cmd_part[0]  # Remove the command name
    command_client_pair=[]
    clients_list=[]
    commands_list=[]
    clients_num=0
    for part in cmd_part:
        if part.startswith("(") and part.endswith(")"):
            try:
                clients_num+=1
                client_part=ast.literal_eval(part)
                clients_list.append(client_part)
                print(f"client part: {clients_list}")
            except Exception as e:
                print(f"Error evaluating part '{part}': {e}")
        else:
            if clients_num!=0:
                command_client_pair.append([commands_list, clients_list])
                clients_num=0
                clients_list=[]
                commands_list=[]
            commands_list.append(part)
            print(f"command part: {commands_list}")
    if clients_num!=0:
        print([commands_list, clients_list])
        command_client_pair.append([commands_list, clients_list])
        clients_num=0
        clients_list=[]
        commands_list=[]
    for pair in command_client_pair:
        for msg in pair[0]:
            command_msg="/command"+" "+shlex.quote(msg)+" "
            for client in pair[1]:
                temp_msg=command_msg+shlex.quote(str(client))+"\n"
                client_socket=client_class[client]["socket"]
                server_instance.send_message(
                    client_socket=client_socket, message=temp_msg)
                print(f"Sending command to clients: {command_msg}")

def _command_handler_server_setup(sock, addr, cmd):
    print(f"Received command from {addr}: {cmd}")

def client_setup():
    global client_instance
    client_instance=connect_tcp.TCP_Client_Base(
        host='127.0.0.1', port=65000,
        client_host='127.0.0.1', is_input_command_in_console=True,
        is_extend_command=True)
    _setup_client_command()
    client_instance.start_TCP_client()

def server_setup():
    global server_instance
    server_instance=connect_tcp.TCP_Server_Base(
        host='127.0.0.1', port=65000, max_clients=10,
        is_input_command_in_console=True, is_extend_command=True)
    _setup_command()
    server_instance.start_TCP_Server()

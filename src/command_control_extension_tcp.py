import os
import sys
import uuid
import shlex
import logging
import subprocess
import threading
import time
import ast
import json
from . import connect_tcp
from datetime import datetime

server_instance=None
client_instance=None
command_counter=0
command_counter_lock=threading.Lock()

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
    global command_counter
    print(f"Received command from {addr}: {cmd}")    
    try:
        cmd_parts = shlex.split(cmd)
    except Exception as e:
        print(f"Error parsing command: {e}")
        return
    if len(cmd_parts) < 3 or cmd_parts[0] != '/command':
        print("Invalid command format.")
        return
    command = cmd_parts[1]
    client_addr = cmd_parts[2]
    with command_counter_lock:
        command_counter += 1
        cmd_id = command_counter
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_filename = f"{cmd_id}.json"
    log_path = os.path.join(log_dir, log_filename)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True)
        output = result.stdout.strip()
        error = result.stderr.strip()
        returncode = result.returncode
    except Exception as e:
        output = ''
        error = str(e)
        returncode = -1
    log_line = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "client": client_addr,
        "from": str(addr),
        "output": output,
        "error": error,
        "returncode": returncode}
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            try:
                log_data = json.load(f)
            except Exception:
                log_data = {}
    else:
        log_data = {}
    if command not in log_data:
        log_data[command] = []
    log_data[command].append(log_line)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    print(f"Log written to {log_path}")
    msg="/file \"{}\"".format(log_path)
    client_instance.file_transfer_client_recv_client_start(
        message=msg, file_folder_abspath=None)

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

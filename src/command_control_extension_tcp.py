import os
import ast
import json
import copy
import shlex
import shutil
import traceback
import threading
import subprocess
from . import connect_tcp
from datetime import datetime
server_instance=None
client_instance=None
command_counter={}
command_counter_lock=threading.Lock()

def _load_json_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _merge_log_dicts(base_data, extra_data):
    merged = {}
    for command, entries in base_data.items():
        merged[command] = list(entries) if isinstance(entries, list) else [entries]
    for command, entries in extra_data.items():
        if command not in merged:
            merged[command] = []
        if isinstance(entries, list):
            merged[command].extend(entries)
        else:
            merged[command].append(entries)
    return merged


def _merge_all_logs(log_dir, merged_filename='merged_logs.json'):
    merged_data = {}
    abs_log_dir = os.path.abspath(log_dir)
    for filename in os.listdir(abs_log_dir):
        if not filename.endswith('.json') or filename == merged_filename:
            continue
        file_path = os.path.join(abs_log_dir, filename)
        if os.path.isfile(file_path):
            file_data = _load_json_file(file_path)
            if file_data:  # 仅当非空时才合并
                merged_data = _merge_log_dicts(merged_data, file_data)
    with open(os.path.join(abs_log_dir, merged_filename), 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)


def _setup_command():
    print("Setting up server command...")
    server_instance.register_command(
        command_name="/command", handler=_command_handler,
        where_to_run="client", run_in_thread=True)
    server_instance.register_command(
        command_name="/command_done", handler=_command_done_dealing_server,
        where_to_run="server", run_in_thread=True)

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
    client_id=0
    for pair in command_client_pair:
        for msg in pair[0]:
            command_msg=("/command"+" "+shlex.quote(msg)+" "+
                         shlex.quote(str(len(pair[0])))+" ")
            for client in pair[1]:
                temp_msg=(command_msg+shlex.quote(str(client_id))+
                          " "+shlex.quote(str(client))+"\n")
                client_socket=client_class[client]["socket"]
                server_instance.send_message(
                    client_socket=client_socket, message=temp_msg)
                print(f"Sending command to clients: {command_msg}")
            client_id+=1

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
    client_addr = cmd_parts[4]
    command_total_num=int(cmd_parts[2])
    client_id=cmd_parts[3]
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    with command_counter_lock:
        if str(client_id) not in command_counter:
            command_counter[str(client_id)]=1
        else:
            command_counter[str(client_id)] += 1
        cmd_id = copy.copy(command_counter[str(client_id)])
    log_filename = "logs{}.json".format("_"+str(client_id))
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
        "cmd_id": str(cmd_id),
        "client_id": str(client_id),
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
    if cmd_id==command_total_num:
        command_counter[str(client_id)]=0
        client_instance.file_transfer_client_recv_client_start(
            message=msg, file_folder_abspath=None)
        client_instance.send_message(
            client_socket=client_instance.client_socket,
            message="/command_done \"{}\" \"{}\"".format(log_filename, log_path))
    else:
        pass
    print("Dealing the command seccessfully!")

def _command_done_dealing_server(sock, addr, cmd):
    cmd_parts = shlex.split(cmd)
    log_filename = cmd_parts[1]
    log_path = cmd_parts[2]
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    received_log_file = os.path.join(
        server_instance.file_transfer_dir,
        os.path.basename(log_path))
    destination_log_file = os.path.join(log_dir, log_filename)
    try:
        if os.path.exists(destination_log_file):
            existing_logs = _load_json_file(destination_log_file)
            incoming_logs = _load_json_file(received_log_file)
            merged_logs = _merge_log_dicts(existing_logs, incoming_logs)
            with open(destination_log_file, 'w', encoding='utf-8') as f:
                json.dump(merged_logs, f, ensure_ascii=False, indent=2)
            os.remove(received_log_file)
        else:
            shutil.move(received_log_file, destination_log_file)
        _merge_all_logs(log_dir)
        merged_data = {}
        for filename in os.listdir(log_dir):
            if not filename.endswith('.json') or filename == 'merged_logs.json':
                continue
            file_path = os.path.join(log_dir, filename)
            if os.path.isfile(file_path):
                file_data = _load_json_file(file_path)
                merged_data = _merge_log_dicts(merged_data, file_data)
        merged_file_path = os.path.join(log_dir, 'merged_logs.json')
        with open(merged_file_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        print("Command Done!")
    except Exception:
        traceback.print_exc()
        print("ErrorWhileMovingTheLogFile: moving log file failed.")

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

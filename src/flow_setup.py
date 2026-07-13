import os
import sys
import json
import shutil
import platform
import tempfile
import argparse
import subprocess
import traceback
from .network_api.connect_tcp import TCP_Server_Base, TCP_Client_Base

SERVER_DEFAULTS = {
    'host': '127.0.0.1',
    'port': 65432,
    'max_clients': 10,
    'port_add_step': 1,
    'port_range_num': 100,
    'max_file_transfer_thread_num': 10,
    'is_hand_alloc_port': False,
    'is_input_command_in_console': True,
    'max_custom_workers': 10,
    'is_extend_command': False
}

CLIENT_DEFAULTS = {
    'host': None,
    'client_host': '127.0.0.1',
    'port': 65432,
    'client_port': None,
    'timeout': None,
    'port_add_step': 1,
    'max_thread_num': 10,
    'is_input_command_in_console': True,
    'is_wait_server': True,
    'max_custom_workers': 10,
    'is_extend_command': False
}

def parse_addr_port(addr_port):
    host, port_str = addr_port.strip().split(':')
    return host, int(port_str)

def load_existing_config():
    if os.path.exists('setup.json'):
        with open('setup.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'servers': [], 'clients': []}

def complete_server_config(cfg):
    full = SERVER_DEFAULTS.copy()
    full.update(cfg)
    return full

def complete_client_config(cfg):
    full = CLIENT_DEFAULTS.copy()
    full.update(cfg)
    return full

def save_config(servers, clients):
    if servers:
        servers = [servers[-1]]
    else:
        servers = []
    if clients:
        clients = [clients[-1]]
    else:
        clients = []
    data = {
        'servers': [complete_server_config(cfg) for cfg in servers],
        'clients': [complete_client_config(cfg) for cfg in clients]
    }
    with open('setup.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def launch_instance(config, instance_type):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(config, f)
        config_file_path = f.name
    script = os.path.abspath(__file__)
    python = sys.executable
    launch_arg = f'--launch_{instance_type}'
    system = platform.system()
    try:
        if system == 'Windows':
            cmd = f'start cmd /k {python} {script} {launch_arg} --config-file "{config_file_path}"'
            subprocess.Popen(cmd, shell=True)
        elif system == 'Linux':
            terminals = ['gnome-terminal', 'xterm', 'x-terminal-emulator']
            launched = False
            for term in terminals:
                if shutil.which(term):
                    cmd = f'{term} -- {python} {script} {launch_arg} --config-file "{config_file_path}"'
                    subprocess.Popen(cmd, shell=True)
                    launched = True
                    break
            if not launched:
                subprocess.Popen(
                    [python, script, launch_arg, '--config-file', config_file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True
                )
        elif system == 'Darwin':
            cmd = f'open -a Terminal.app {python} {script} {launch_arg} --config-file "{config_file_path}"'
            subprocess.Popen(cmd, shell=True)
        else:
            subprocess.Popen(
                [python, script, launch_arg, '--config-file', config_file_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
    except Exception as e:
        print(f"Failed to launch instance: {e}")
        traceback.print_exc()
        try:
            os.unlink(config_file_path)
        except:
            pass

def interactive_collect():
    servers = []
    clients = []
    while True:
        print("\n--- Add New Instance ---")
        while True:
            type_choice = input("Select type (0=Server, 1=Client): ").strip()
            if type_choice in ('0', '1'):
                break
            print("Invalid input, please enter 0 or 1")
        is_server = (type_choice == '0')
        while True:
            setup_addr = input("Enter bind address and port (format host:port): ").strip()
            try:
                host, port = parse_addr_port(setup_addr)
                break
            except:
                print("Invalid format, please retry")
        if is_server:
            config = {'host': host, 'port': port}
            servers = [config]
            print(f"Server config set to: {host}:{port}")
        else:
            while True:
                conn_addr = input("Enter server address and port to connect (format host:port): ").strip()
                try:
                    srv_host, srv_port = parse_addr_port(conn_addr)
                    break
                except:
                    print("Invalid format, please retry")
            config = {
                'client_host': host,
                'client_port': port,
                'host': srv_host,
                'port': srv_port
            }
            clients = [config]
            print(f"Client config set to: local {host}:{port} -> server {srv_host}:{srv_port}")
        cont = input("Continue adding more instances? (Y/N): ").strip().lower()
        if cont != 'y':
            break
    return servers, clients

def generate_configs_from_args(args):
    if args.setup_num > 1:
        print("Warning: --setup_num is ignored because only one instance per type is allowed.")
    host, port = parse_addr_port(args.setup_addr_port)
    if args.type == 0:
        config = {'host': host, 'port': port}
        return [config], []
    else:
        srv_host, srv_port = parse_addr_port(args.connect_addr_port)
        config = {
            'client_host': host,
            'client_port': port,
            'host': srv_host,
            'port': srv_port
        }
        return [], [config]

def run_launched_instance(instance_type, config_file_path):
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        try:
            os.unlink(config_file_path)
        except:
            pass
        if instance_type == 'server':
            server = TCP_Server_Base(**config)
        else:
            client = TCP_Client_Base(**config)
    except Exception as e:
        print(f"Failed to start instance: {e}")
        traceback.print_exc()
        input("Press any key to exit...")
        sys.exit(1)

def main():
    if '--launch_server' in sys.argv:
        idx = sys.argv.index('--launch_server')
        try:
            cfg_idx = sys.argv.index('--config-file', idx)
            if cfg_idx + 1 < len(sys.argv):
                config_file = sys.argv[cfg_idx + 1]
                run_launched_instance('server', config_file)
            else:
                print("Error: missing --config-file argument")
                sys.exit(1)
        except ValueError:
            print("Error: missing --config-file argument")
            sys.exit(1)
        return
    if '--launch_client' in sys.argv:
        idx = sys.argv.index('--launch_client')
        try:
            cfg_idx = sys.argv.index('--config-file', idx)
            if cfg_idx + 1 < len(sys.argv):
                config_file = sys.argv[cfg_idx + 1]
                run_launched_instance('client', config_file)
            else:
                print("Error: missing --config-file argument")
                sys.exit(1)
        except ValueError:
            print("Error: missing --config-file argument")
            sys.exit(1)
        return
    parser = argparse.ArgumentParser(description='Flow Setup Launcher')
    parser.add_argument('--type', type=int, choices=[0, 1],
                        help='0=Server, 1=Client')
    parser.add_argument('--setup_addr_port', type=str,
                        help='Bind address and port (host:port)')
    parser.add_argument('--connect_addr_port', type=str,
                        help='Server address and port to connect (client required)')
    parser.add_argument('--setup_num', type=int, default=1,
                        help='Number of instances to launch (only 1 is allowed)')
    args = parser.parse_args()
    if args.type is not None:
        if args.type == 0 and args.connect_addr_port is not None:
            print("Error: --connect_addr_port cannot be used in Server mode")
            sys.exit(1)
        if args.type == 1 and (args.setup_addr_port is None or args.connect_addr_port is None):
            print("Error: Client mode requires both --setup_addr_port and --connect_addr_port")
            sys.exit(1)
        if args.type == 0 and args.setup_addr_port is None:
            print("Error: Server mode requires --setup_addr_port")
            sys.exit(1)
        servers, clients = generate_configs_from_args(args)
        save_config(servers, clients)
        for cfg in servers:
            launch_instance(cfg, 'server')
        for cfg in clients:
            launch_instance(cfg, 'client')
        return
    if os.path.exists('setup.json'):
        choice = input("setup.json exists. Overwrite configuration data? (Y/N): ").strip().lower()
        if choice == 'n':
            config_data = load_existing_config()
            for cfg in config_data.get('servers', []):
                launch_instance(cfg, 'server')
            for cfg in config_data.get('clients', []):
                launch_instance(cfg, 'client')
            return
    else:
        choice = 'y'
    servers, clients = interactive_collect()
    save_config(servers, clients)
    for cfg in servers:
        launch_instance(cfg, 'server')
    for cfg in clients:
        launch_instance(cfg, 'client')

if __name__ == '__main__':
    main()

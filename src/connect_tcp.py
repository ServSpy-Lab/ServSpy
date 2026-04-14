import os
import ast
import sys
import time
import copy
import shlex
import socket
import traceback
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
class TCP_Server_Base:  # TCP server class
    def __init__(self, host='127.0.0.1', port=65432,
                 max_clients=10, port_add_step=1, port_range_num=100,
                 max_file_transfer_thread_num=10, is_hand_alloc_port=False,
                 is_input_command_in_console=True, max_custom_workers=10,
                 is_extend_command=False):
        self.project_dir=os.path.dirname(os.path.abspath(__file__))
        self.project_info_dir=os.path.join(self.project_dir, '.ServSpy')
        if os.path.exists(self.project_info_dir)==False:
            os.mkdir(self.project_info_dir)
        self.project_temp_info_dir=os.path.join(
            self.project_info_dir, 'temp_info')
        if os.path.exists(self.project_temp_info_dir)==False:
            os.mkdir(self.project_temp_info_dir)
        self.server_port_lock_file=os.path.join(
            self.project_temp_info_dir, 'server_port_lock.lock')
        self.decode_command_table_file_path=os.path.join(
            self.project_dir, 'decode_command_table.json')
        self.file_transfer_dir=os.path.join(
            self.project_dir, 'received_files')
        self.host = host
        self.port = port
        self.all_alloced_ports_list=[self.port]
        self.max_clients = max_clients
        self.is_hand_alloc_port=is_hand_alloc_port
        self.is_input_command_in_console=is_input_command_in_console
        self.alloc_port(port_add_step, port_range_num)
        self.server_socket = None
        self.clients = {}  # store client info
        self.file_client_id_lock=threading.Lock()
        self.file_transfer_server_port_lock=threading.Lock()
        self.file_server_port_list=[]
        self.file_client_id=0
        self.running = False
        self.client_lock = threading.Lock()  # add the threading lock
        self.max_file_transfer_thread_num=max_file_transfer_thread_num
        MAX_CONCURRENT_FILES = self.max_file_transfer_thread_num
        self.file_semaphore = threading.Semaphore(MAX_CONCURRENT_FILES)
        self.command_decode_table_str=None
        with open(self.decode_command_table_file_path, 'r', encoding='utf-8') as f:
            self.command_decode_table_str = f.read()
        self.command_decode_table=(
            ast.literal_eval(self.command_decode_table_str))
        self.send_file_header_sign = (
            self.command_decode_table[0]["file_send_server_header"])
        self.send_file_data_sign = (
            self.command_decode_table[0]["file_send_server_data"])
        self.server_reseived_file_header_sign = (
            self.command_decode_table[0]["file_resieve_client_header"])
        self.server_reseived_file_data_sign = (
            self.command_decode_table[0]["file_resieve_client_data"])
        self.server_start_file_transfer_sign = (
            self.command_decode_table[0]["file_send_server_start_file_transfer"])
        self.error_sign=(
            self.command_decode_table[0]["file_send_resieve_error"])
        self._custom_handlers = [{}, {}]
        self._custom_handler_threaded = [{}, {}]
        self._custom_executor = ThreadPoolExecutor(max_workers=max_custom_workers)
        self._task_semaphore = threading.Semaphore(max_custom_workers)
        self.is_extend_command=is_extend_command
        if self.is_extend_command:
            pass
        else:
            self.start_TCP_Server()
    def alloc_port(self, port_add_step, port_range_num):
        if self.is_hand_alloc_port==True:
            while self.is_server_port_temp_info_file_locked():
                time.sleep(0.1)
            self.server_port_temp_info_file_lock()
            self.hand_alloc_port(port_add_step, port_range_num)
            self.server_port_temp_info_file_unlock()
    def free_port(self):
        if self.is_hand_alloc_port==True:
            while self.is_server_port_temp_info_file_locked():
                time.sleep(0.1)
            self.server_port_temp_info_file_lock()
            self.hand_free_port()
            self.server_port_temp_info_file_unlock()
    def server_port_temp_info_file_lock(self):
        with open(self.server_port_lock_file, 'w', encoding='utf-8') as f:
            f.write("locked")
    def is_server_port_temp_info_file_locked(self):
        if os.path.exists(self.server_port_lock_file):
            return True
        else:
            return False
    def server_port_temp_info_file_unlock(self):
        if os.path.exists(self.server_port_lock_file):
            os.remove(self.server_port_lock_file)
    def hand_alloc_port(self, port_add_step, port_range_num):
        self.port_temp_info_path=os.path.join(
            self.project_temp_info_dir, 'server_port_info.log')
        client_port_temp_info_file_path=os.path.join(
            self.project_temp_info_dir, 'clients_port_info.log')
        if os.path.exists(client_port_temp_info_file_path):
            print("Warning: client port info file exists, means the client has already allocated a port, may cause port conflict!")
        self.port_add_step = port_add_step
        self.port_range_num = port_range_num
        self.add_latest_port=self.port+1
        self.minus_latest_port=self.port
        self.alloc_add_port_lock=threading.Lock()
        self.alloc_minus_port_lock=threading.Lock()
        self.each_client_port_range=int(self.port_range_num/self.max_clients)
        if os.path.exists(self.port_temp_info_path)==False:
            self.server_num=0
            self.server_port_info=[]
            self.min_port=self.port-self.port_add_step*self.port_range_num
            self.max_port=self.port+1+self.port_add_step*self.port_range_num
            each_server_info={
                "server_id": self.server_num,
                "host": self.host,
                "port": self.port,
                "min_port": self.min_port,
                "max_port": self.max_port,
                "is_running": self.running}
            self.server_port_info.append(each_server_info)
            with open(self.port_temp_info_path, 'w', encoding='utf-8') as f:
                f.write(str(self.server_port_info))
        else:
            with open(self.port_temp_info_path, 'r', encoding='utf-8') as f:
                self.server_port_info=ast.literal_eval(f.read())
            self.server_num=(
                self.server_port_info[len(self.server_port_info)-1]["server_id"]+1)
            auto_port_add=(
                self.server_port_info[len(self.server_port_info)-1]["max_port"]+
                self.port_add_step*self.port_range_num+1)
            auto_port_minus=(
                self.server_port_info[len(self.server_port_info)-1]["min_port"]-
                self.port_add_step*self.port_range_num-1)
            if self.port>auto_port_minus and self.port<auto_port_add:
                self.port=auto_port_add
            self.min_port=self.port-self.port_add_step*self.port_range_num
            self.max_port=self.port+1+self.port_add_step*self.port_range_num
            each_server_info={
                "server_id": self.server_num,
                "host": self.host,
                "port": self.port,
                "min_port": self.min_port,
                "max_port": self.max_port,
                "is_running": self.running}
            self.server_port_info.append(each_server_info)
            for is_running in range(len(self.server_port_info)-1, -1, -1):
                if self.server_port_info[is_running]["is_running"]==False:
                    del self.server_port_info[is_running]
            with open(self.port_temp_info_path, 'w', encoding='utf-8') as f:
                f.write(str(self.server_port_info))
    def hand_free_port(self):
        self.port_temp_info_path=os.path.join(
            self.project_temp_info_dir, 'server_port_info.log')
        if os.path.exists(self.port_temp_info_path):
            with open(self.port_temp_info_path, 'r', encoding='utf-8') as f:
                self.server_port_info=ast.literal_eval(f.read())
            for server_num in range(len(self.server_port_info)):
                if self.server_port_info[server_num]["server_id"]==self.server_num:
                    del self.server_port_info[server_num]
            if len(self.server_port_info)==0:
                os.remove(self.port_temp_info_path)
            else:
                with open(self.port_temp_info_path, 'w', encoding='utf-8') as f:
                    f.write(str(self.server_port_info))
    def palloc(self):
        alloc_port=0
        while True:
            alloc_port=self.file_palloc()
            time.sleep(0.1)
            if alloc_port is not None:
                return alloc_port
            else:
                alloc_port=self.spy_palloc()
                if alloc_port is not None:
                    return alloc_port
                else:
                    pass
    def pfree(self, port):
        self.file_pfree(port)
        self.spy_pfree(port)
    def file_palloc(self):
        if self.is_hand_alloc_port:
            with self.alloc_add_port_lock:
                if self.add_latest_port + self.port_add_step > self.max_port:
                    for step in range(self.port+1, self.max_port, self.port_add_step):
                        if step in self.all_alloced_ports_list:
                            pass
                        else:
                            alloced_port=step
                            self.all_alloced_ports_list.append(alloced_port)
                            return alloced_port
                    return None
                self.add_latest_port += self.port_add_step
                self.all_alloced_ports_list.append(self.add_latest_port)
                return self.add_latest_port
        else:
            return 0
    def file_pfree(self, port):
        if self.is_hand_alloc_port:
            with self.alloc_add_port_lock:
                if port in self.all_alloced_ports_list:
                    self.all_alloced_ports_list.remove(port)
                    print(
                        "releasing file transfer port, current latest port:", port)
                self.add_latest_port-=self.port_add_step
        else:
            pass
    def spy_palloc(self):
        if self.is_hand_alloc_port:
            with self.alloc_minus_port_lock:
                if self.minus_latest_port - self.port_add_step < self.min_port:
                    for step in range(self.port, self.min_port, -self.port_add_step):
                        if step in self.all_alloced_ports_list:
                            pass
                        else:
                            alloced_port=step
                            self.all_alloced_ports_list.append(alloced_port)
                            return alloced_port
                    return None
                self.minus_latest_port -= self.port_add_step
                self.all_alloced_ports_list.append(self.minus_latest_port)
                return self.minus_latest_port
        else:
            return 0
    def spy_pfree(self, port):
        if self.is_hand_alloc_port:
            with self.alloc_minus_port_lock:
                if port in self.all_alloced_ports_list:
                    self.all_alloced_ports_list.remove(port)
                self.minus_latest_port+=self.port_add_step
        else:
            pass
    def register_command(self, command_name, handler, where_to_run, run_in_thread=False):
        registe_index=None
        if where_to_run=="server":
            registe_index=0
        elif where_to_run=="client":
            registe_index=1
        else:
            print(f"Invalid where_to_run value: {where_to_run}, must be 'server' or 'client'")
            return False
        self._custom_handlers[registe_index][command_name] = handler
        self._custom_handler_threaded[registe_index][command_name] = run_in_thread
    def submit_task(self, func, *args, **kwargs):
        self._task_semaphore.acquire()
        future = self._custom_executor.submit(func, *args, **kwargs)
        future.add_done_callback(lambda f: self._task_semaphore.release())
        return future
    def create_temporary_server(self, handler, port=None, max_connections=1):
        if port is None:
            port = self.palloc()
            if port is None:
                raise RuntimeError("No available port for temporary server")
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, port))
        server_socket.listen(max_connections)
        stop_event = threading.Event()
        def server_loop():
            while not stop_event.is_set():
                try:
                    server_socket.settimeout(1.0)
                    client_sock, addr = server_socket.accept()
                    threading.Thread(target=handler,
                                     args=(client_sock, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if not stop_event.is_set():
                        print(f"Temporary server error: {e}")
                    break
            server_socket.close()
            self.pfree(port)
        server_thread = threading.Thread(target=server_loop, daemon=True)
        server_thread.start()
        return port, server_thread, stop_event
    def create_temporary_client(self, server_host, server_port, bind_port=None, on_data=None):
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if bind_port is not None:
            client_sock.bind((self.host, bind_port))
        client_sock.connect((server_host, server_port))
        stop_event = threading.Event()
        def receiver():
            while not stop_event.is_set():
                try:
                    client_sock.settimeout(1.0)
                    data = self.recieve_message(client_sock, 4096)
                    if not data:
                        break
                    if on_data:
                        on_data(data, client_sock)
                except socket.timeout:
                    continue
                except:
                    break
            client_sock.close()
        recv_thread = threading.Thread(target=receiver, daemon=True)
        recv_thread.start()
        return client_sock, recv_thread, stop_event
    def broadcast(self, message, exclude_client=None): # broadcast message to all clients except exclude_client
        with self.client_lock:
            disconnected_clients = []
            for addr, client_info in self.clients.items():
                if exclude_client and addr == exclude_client:
                    continue
                try:
                    self.send_message(client_info['socket'], message)
                except:
                    disconnected_clients.append(addr)
                    traceback.print_exc()
            for addr in disconnected_clients:  # del disconnected clients
                if addr in self.clients:
                    print(f"deleting the disconnected client: {addr}")
                    self.clients[addr]['socket'].close()
                    del self.clients[addr]
    def send_msg_to_specific_client(self, message):  # send message to specific client by client address
        command_part=shlex.split(message)
        del command_part[0]
        client_message_pair_list=[]
        client_list=[]
        msg_list=[]
        client_addr_times=0
        for command_part_index in range(len(command_part)):
            part=command_part[command_part_index]
            if part.startswith("(") and part.endswith(")"):
                try:
                    client_addr=ast.literal_eval(part)
                    client_list.append(client_addr)
                    client_addr_times+=1
                    if command_part_index==len(command_part)-1:
                        client_message_pair=[client_list, msg_list]
                        client_message_pair_list.append(client_message_pair)
                except:
                    traceback.print_exc()
                    print(f"ErrorWhileParsingClientAddress: {part} is not a valid client address, skipped")
            else:
                if client_addr_times!=0:
                    client_message_pair=[client_list, msg_list]
                    client_message_pair_list.append(client_message_pair)
                    client_list=[]
                    msg_list=[]
                    msg_list.append(part)
                    client_addr_times=0
                else:
                    msg_list.append(part)
        for each_client_message_pair in client_message_pair_list:
            for client_addr in each_client_message_pair[0]:
                for msg in each_client_message_pair[1]:
                    if client_addr in self.clients:
                        client_socket=self.clients[client_addr]['socket']
                        self.send_message(client_socket, msg)
                    else:
                        print(f"Client {client_addr} not found, cannot send message: {msg}")
    def send_message(self, client_socket, message):  # send message to specific client
        if not self.running or not client_socket:
            print("disable the connect to server")
            return False
        try:  # add newline character for server to distinguish messages
            if isinstance(message, str):
                deal_msg = message.strip()
                if not deal_msg.endswith('\n'):
                    deal_msg += '\n'
                data = deal_msg.encode('utf-8')
            elif isinstance(message, bytes):
                data = message
            else:
                print(f"Unsupported message type: {type(message)}")
                return False
            client_socket.sendall(data)
            return True
        except Exception as e:
            print(f"send msg error: {e}")
            traceback.print_exc()
            return False
    def recieve_message(self, client_socket, msg_length):  # receive message
        data=client_socket.recv(msg_length)
        return data
    def handle_client(self, client_socket, client_address):  # deal with each client
        client_id = f"{client_address[0]}:{client_address[1]}"
        with self.client_lock: # add new client
            self.clients[client_address] = {
                'socket': client_socket,
                'address': client_address,
                'id': client_id,
                'connected_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        print(f"new connection: {client_id}")
        print(f"connection count mount: {len(self.clients)}")
        welcome_msg = f"Welcome!: {client_id}\n"  # send welcome message
        self.send_message(client_socket, welcome_msg)
        if self.is_hand_alloc_port==True:
            broadcast_clients_port_alloc_range_msg="/client_alloc_port_range {}".format(
                self.each_client_port_range)
            self.broadcast(broadcast_clients_port_alloc_range_msg)
        else:
            broadcast_clients_port_alloc_range_msg="/client_alloc_port_range NO_LIMIT"
            self.broadcast(broadcast_clients_port_alloc_range_msg)
        print(self.clients)
        buffer=""
        try:
            while True:
                data = self.recieve_message(client_socket, 4096)  # get msg from client
                print(data)
                if not data:
                    break
                buffer+=data.decode("utf-8")
                while '\n' in buffer:  # deal with multiple messages in buffer
                    line, buffer = buffer.split('\n', 1)
                    message = line.strip()
                    if not message:
                        continue
                    print(message)
                    if message.startswith('/'):  # deal with special command
                        response = self.handle_command(
                            client_socket, client_address, message)
                    else:
                        timestamp = datetime.now().strftime("%H:%M:%S")  # deal with normal message
                        log_msg = f"[{timestamp}] {client_id}: {message}"
                        print(log_msg)
                        response = f"msg send: {message}"
                    if response:  # send response to client
                        self.send_message(client_socket, response)
        except ConnectionResetError:
            print(f"client disconnected: {client_id}")
            traceback.print_exc()
        except Exception as e:
            print(f"error while deal with client {client_id} : {e}")
            traceback.print_exc()
        finally:
            with self.client_lock:
                if client_address in self.clients:
                    del self.clients[client_address]
            client_socket.close()
            print(f"client disconnected: {client_id}")
            print(f"current connection count: {len(self.clients)}")
    def handle_command(self, client_socket, client_address, command):  # deal with special commands from client
        print(client_socket, client_address, command)
        client_id = f"{client_address[0]}:{client_address[1]}"
        send_str=None
        if command == '/help':
            help_text=["avalable commands:",
                        "/help - print help meg\n",
                        "\t/time - display server time\n",
                        "\t/clients - display connected clients\n",
                        "\t/file <file_path> - send file to server\n",
                        "\t/multiple_file <file1> <file2> ... ",
                        "- send multiple files to server\n",
                        "\t/file_folder <folder_path> - send folder to server\n",
                        "\t/multiple_file_folder <folder1> <folder2> ... ",
                        "- send multiple folders to server\n",
                        "\t/quit - disconnect"]
            send_str=" ".join(help_text)+"\n"
            return send_str
        elif command == '/time':
            send_str=(
                f"server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"+"\n")
            return send_str
        elif command == '/clients':
            with self.client_lock:
                client_list = [info['id'] for info in self.clients.values()]
                send_str=(
                    f"online clients ({len(client_list)}): {', '.join(client_list)}"+"\n")
                return send_str
        elif command == '/quit':
            send_str="Bye!"+"\n"
            return send_str
        elif shlex.split(command.lower())[0] == "/file":
            self.file_transfer_server_recv_server_start_thread(
                client_id, client_socket, command)
        elif shlex.split(command.lower())[0] == "/file_folder":
            self.file_folder_transfer_server_recv_server_start_thread(
                command, client_id, client_socket)
        elif shlex.split(command.lower())[0] == "/server_file_transfer_port":
            with self.file_transfer_server_port_lock:
                self.file_transfer_server_port=int(command.split(" ")[1])
                try:
                    file_client_id=int(command.split(" ")[2])
                    self.file_server_port_list.append(
                        [self.file_transfer_server_port, file_client_id])
                except:
                    traceback.print_exc()
                    pass
        else:
            cmd_parts = shlex.split(command.strip())
            if not cmd_parts:
                return None
            cmd_name = cmd_parts[0].lower()
            if (cmd_name in self._custom_handlers[0]):
                handler = self._custom_handlers[0][cmd_name]
                run_in_thread = self._custom_handler_threaded[0].get(
                    cmd_name, False)
                if run_in_thread:
                    self._custom_executor.submit(
                        self._execute_custom_handler, handler, command,
                        client_socket, client_address)
                    return "Command received, processing in background.\n"
                else:
                    response = self._execute_custom_handler(
                        handler, command, client_socket, client_address)
                    return response
            else:
                print(f"Unknown command: {command}")
    def _execute_custom_handler(self, handler, command, client_socket=None, client_address=None):
        try:
            result = handler(client_socket, client_address, command)
            if result is not None:
                if isinstance(result, str) and not result.endswith('\n'):
                    result += '\n'
                try:
                    self.send_message(client_socket, result)
                except Exception as e:
                    print(f"Error sending message: {e}")
                return result
            return None
        except Exception as e:
            error_msg = f"Error in custom command handler: {e}\n"
            traceback.print_exc()
            try:
                self.send_message(client_socket, error_msg)
            except Exception as e:
                print(f"Error sending error message: {e}")
            return error_msg
    def file_folder_transfer_server_recv_server_start_thread(  # start a file folder server thread on server
            self, command, client_id, client_socket):
        relative_folder_path=shlex.split(command)[1]
        try:
            file_name=shlex.split(command)[2]
            folder_transfer_server_recv_server_start_thread=threading.Thread(
                target=self.file_transfer_server_recv_server_start,
                args=(client_id, client_socket, command, relative_folder_path, file_name),
                daemon=True)
            folder_transfer_server_recv_server_start_thread.start()
        except:
            folder_transfer_server_recv_server_start_thread=threading.Thread(
                target=self.file_transfer_server_recv_server_start,
                args=(client_id, client_socket, command, relative_folder_path),
                daemon=True)
            folder_transfer_server_recv_server_start_thread.start()
    def file_transfer_server_recv_server_start_thread(  # start a file server thread on server
            self, client_id, client_socket, command):
        file_transfer_server_recv_server_start_thread=threading.Thread(
                target=self.file_transfer_server_recv_server_start,
                args=(client_id, client_socket, command),
                daemon=True)
        file_transfer_server_recv_server_start_thread.start()
    def file_transfer_server_recv_server_start(  # deal with file transfer request server on server from client and receive file from client
            self, client_id, client_socket, command, new_save_path=None, file_name=None):
        file_transfer_server_port=self.palloc()
        self.file_transfer_mode_recv(
            self.host, file_transfer_server_port,
            client_socket, client_id, new_save_path, file_name, command)
        self.pfree(file_transfer_server_port)
    def file_transfer_mode_recv(self, server_file_address, server_file_port,
                                client_socket, client_id, new_save_path, file_name, command):
        file_running=True
        client_file_socket=None
        server_file_socket=None
        save_path=None
        def close_socket():
            nonlocal file_running
            nonlocal client_file_socket
            nonlocal server_file_socket
            file_running=False
            client_file_socket.close()
            server_file_socket.close()
        def setting_file_save_path():
            nonlocal save_path
            save_path = self.file_transfer_dir
            if new_save_path:
                path_list=new_save_path.split("/")
                del path_list[0]
                for node in path_list:
                    save_path = os.path.join(save_path, node)
                    os.makedirs(save_path, exist_ok=True)
            if file_name or new_save_path==None:
                return save_path
            close_socket()
            return None
        def file_transfer_client_recv(client_id):
            nonlocal file_running
            nonlocal client_file_socket
            nonlocal server_file_socket
            nonlocal save_path
            filename = None
            self.send_message(client_file_socket,
                              self.server_start_file_transfer_sign)
            try:
                name_len_bytes = b''
                while len(name_len_bytes) < 4:
                    chunk = self.recieve_message(
                        client_file_socket, 4 - len(name_len_bytes))
                    print(chunk)
                    if not chunk:
                        try:
                            self.send_message(client_file_socket,
                                              self.error_sign)
                        except:
                            traceback.print_exc()
                            pass
                        close_socket()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileNameLength: client disconnected")
                    name_len_bytes += chunk
                    if (name_len_bytes.strip()==
                        self.error_sign.encode('utf-8')):
                        close_socket()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileNameLength: client reported error and disconnected")
                name_len = int.from_bytes(name_len_bytes, 'big')
                file_name_encoded = b''
                while len(file_name_encoded) < name_len:
                    chunk = self.recieve_message(
                        client_file_socket, name_len - len(file_name_encoded))
                    if not chunk:
                        try:
                            self.send_message(client_file_socket,
                                              self.error_sign)
                        except:
                            traceback.print_exc()
                            pass
                        close_socket()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileName: client disconnected")
                    file_name_encoded += chunk
                    if (file_name_encoded.strip()==
                        self.error_sign.encode('utf-8')):
                        close_socket()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileName: client reported error and disconnected")
                filename = file_name_encoded.decode('utf-8')
                filename = filename.strip()
                filename = os.path.basename(filename)
                size_bytes = b''
                while len(size_bytes) < 8:
                    chunk = self.recieve_message(
                        client_file_socket, 8 - len(size_bytes))
                    if not chunk:
                        try:
                            self.send_message(client_file_socket,
                                              self.error_sign)
                        except:
                            traceback.print_exc()
                            pass
                        close_socket()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileSize: client disconnected")
                    size_bytes += chunk
                    if (size_bytes.strip()==
                        self.error_sign.encode('utf-8')):
                        close_socket()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileSize: client reported error and disconnected")
                file_size = int.from_bytes(size_bytes, 'big')
                self.send_message(client_file_socket,
                                  self.server_reseived_file_header_sign)
                original_filename = filename
                if file_name:
                    final_filename = file_name.strip()
                else:
                    final_filename = os.path.basename(original_filename)
                full_path = os.path.join(save_path, final_filename).strip()
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path.strip(), 'wb') as f:
                    remaining = file_size
                    while remaining > 0:
                        chunk = self.recieve_message(
                            client_file_socket, min(65536, remaining))
                        if not chunk:
                            try:
                                self.send_message(client_file_socket,
                                                  self.error_sign)
                            except:
                                traceback.print_exc()
                                pass
                            close_socket()
                            raise ConnectionError(
                                "ErrorWhileReceivingFileData: client disconnected")
                        f.write(chunk)
                        remaining -= len(chunk)
                self.send_message(client_file_socket,
                                  self.server_reseived_file_data_sign)
                print(f"file {filename} received from {client_id}, size {file_size} bytes")
                close_socket()
            except Exception as e:
                traceback.print_exc()
                try:
                    self.send_message(client_file_socket,
                                      self.error_sign)
                except:
                    traceback.print_exc()
                    pass
                close_socket()
                print(f"ErrorWhileReceiveFile: {e}")
                return False
            else:
                close_socket()
                return None
        server_file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_file_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_file_socket.bind((server_file_address, server_file_port))
        file_transfer_server_port=server_file_socket.getsockname()[1]
        command_part=shlex.split(command)
        file_client_id=command_part[len(command_part)-1]
        transfer_server_port_msg=(
            "/server_file_transfer_port {} {}\n".format(
                file_transfer_server_port, file_client_id))
        self.send_message(client_socket,
                          transfer_server_port_msg)
        server_file_socket.listen(1)
        try:
            client_file_socket, client_file_address = server_file_socket.accept()
            is_open_file_transfer=setting_file_save_path()
            if is_open_file_transfer==None:
                pass
            else:
                threading.Thread(
                    target=file_transfer_client_recv,
                    args=(client_id, ),
                    daemon=True).start()
        except Exception as e:
            print(f"\nget file transfer msg error: {e}")
            traceback.print_exc()
            close_socket()
        finally:
            server_file_socket.close()
    def diff_multiple_file_diff_multiple_client_transfer_server_recv_client_start(self, message):
        command_part=shlex.split(message)
        del command_part[0]
        file_client_pair_list=[]
        file_list=[]
        client_list=[]
        command_part_addr_times=0
        for command_part_index in range(len(command_part)):
            part=command_part[command_part_index]
            if part.startswith("(") and part.endswith(")"):
                try:
                    client_addr=ast.literal_eval(part)
                    client_list.append(client_addr)
                    command_part_addr_times+=1
                    if command_part_index==len(command_part)-1:
                        file_client_pair=[client_list, file_list]
                        file_client_pair_list.append(file_client_pair)
                except:
                    traceback.print_exc()
            else:
                if command_part_addr_times!=0:
                    file_client_pair=[client_list, file_list]
                    file_client_pair_list.append(file_client_pair)
                    file_list=[]
                    client_list=[]
                    file_list.append(part)
                    command_part_addr_times=0
                else:
                    file_list.append(part)
        for each_file_client_pair in file_client_pair_list:
            file_transfer_command_message=""
            file_folder_transfer_command_message=""
            for file in each_file_client_pair[1]:
                try:
                    if os.path.isfile(file):
                        if file_transfer_command_message=="":
                            file_transfer_command_message="/file {}".format(
                                shlex.quote(file))
                        else:
                            file_transfer_command_message+=" {}".format(
                                shlex.quote(file))
                    elif os.path.isdir(file):
                        if file_folder_transfer_command_message=="":
                            file_folder_transfer_command_message="/file_folder {}".format(
                                shlex.quote(file))
                        else:
                            file_folder_transfer_command_message+=" {}".format(
                                shlex.quote(file))
                except:
                    traceback.print_exc()
                    print(f"ErrorWhileParsingFilePath: {file} is not a valid file or folder path, skipped")
                    pass
            for client_addr in each_file_client_pair[0]:
                if file_transfer_command_message!="":
                    file_transfer_command_message+=" {}".format(
                        shlex.quote(str(client_addr)))
                if file_folder_transfer_command_message!="":
                    file_folder_transfer_command_message+=" {}".format(
                        shlex.quote(str(client_addr)))
            if file_transfer_command_message!="":
                self.multiple_file_multiple_client_transfer_server_recv_client_start(
                    file_transfer_command_message)
            if file_folder_transfer_command_message!="":
                self.multiple_file_multiple_client_transfer_server_recv_client_start(
                    file_folder_transfer_command_message)
    def multiple_file_multiple_client_transfer_server_recv_client_start(self, message):
        command_part=shlex.split(message)
        command_type=command_part[0]
        del command_part[0]
        transfer_file_list=[]
        client_addr_list=[]
        for part in command_part:
            if part.startswith("(") and part.endswith(")"):
                try:
                    client_addr=ast.literal_eval(part)
                    client_addr_list.append(client_addr)
                except:
                    traceback.print_exc()
            else:
                transfer_file_list.append(part)
        for client_addr in client_addr_list:
            for transfer_file in transfer_file_list:
                if command_type=="/file":
                    file_transfer_command_message=(
                        "/file {} {}".format(shlex.quote(transfer_file), 
                                            shlex.quote(str(client_addr))))
                    self.file_transfer_server_recv_client_start_thread(
                        file_transfer_command_message)
                    print(f"start to send file command: {file_transfer_command_message}")
                elif command_type=="/file_folder":
                    folder_transfer_command_message=(
                        "/file_folder {} {}".format(shlex.quote(transfer_file), 
                                            shlex.quote(str(client_addr))))
                    self.folder_file_transfer_server_recv_client_start(
                        folder_transfer_command_message)
                    print(f"start to send folder command: {folder_transfer_command_message}")
    def folder_file_transfer_server_recv_client_start(self, message):
        command_part=shlex.split(message)
        folder_path=command_part[1]
        client_addr=ast.literal_eval(command_part[len(command_part)-1])
        client_socket=self.clients[client_addr]['socket']
        if os.path.isdir(folder_path)==False:
            print(f"{folder_path} is not a valid folder path")
            return False
        base_path=os.path.dirname(folder_path)
        def get_relative_path(base_path, abs_path):
            base = os.path.normpath(base_path)
            abs_ = os.path.normpath(abs_path)
            common = os.path.commonpath([base, abs_])
            if common != base:
                raise ValueError(f"'{abs_path}' is not a subpath of '{base_path}'")
            rel = os.path.relpath(abs_, base)
            if rel == '.':
                return ''
            rel = rel.replace(os.sep, '/')
            return '/' + rel
        def send_folder_transfer_command(folder_path, file_name=None, abspath=None):
            folder_transfer_command_message=(
                "/file_folder {}".format(shlex.quote(folder_path)))
            if file_name:
                each_file_transfer_command_message=(
                    "/file_folder {} {} {}".format(
                        shlex.quote(folder_path), shlex.quote(file_name),
                        shlex.quote(str(client_addr))))
                self.file_transfer_server_recv_client_start_thread(
                    each_file_transfer_command_message, abspath)
                print(f"start to send folder command: {each_file_transfer_command_message}")
            else:
                self.send_message(client_socket,
                                  folder_transfer_command_message.strip())
                print(f"start to send folder command: {folder_transfer_command_message}")
        def start_file_transfer_with_limit(rel_dir, file, root):
            cmd = "/file_folder {} {} {}".format(
                shlex.quote(rel_dir), shlex.quote(file),
                shlex.quote(str(client_addr)))
            def limited_transfer():
                self.file_semaphore.acquire()
                try:
                    self.file_transfer_server_recv_client_start(cmd, root)
                finally:
                    self.file_semaphore.release()
            thread = threading.Thread(target=limited_transfer, daemon=True)
            thread.start()
            print(f"start to send file: {cmd} (limit {self.max_file_transfer_thread_num})")
        def get_all_files_in_folder():
            for root, dirs, files in os.walk(folder_path):
                rel_dir = get_relative_path(base_path, root)
                if root != folder_path:
                    send_folder_transfer_command(rel_dir)
                for file in files:
                    start_file_transfer_with_limit(rel_dir, file, root)
            print(f"finished sending all files in folder {folder_path}")
        transfer_path=get_relative_path(base_path, folder_path)
        send_folder_transfer_command(transfer_path)
        get_all_files_in_folder()
    def file_transfer_server_recv_client_start_thread(self, message, file_folder_abspath=None):
        file_transfer_server_recv_client_start_thread=(
            threading.Thread(
            target=self.file_transfer_server_recv_client_start,
            args=(message, file_folder_abspath),
            daemon=True))
        file_transfer_server_recv_client_start_thread.start()
    def file_transfer_server_recv_client_start(self, message, file_folder_abspath):
        client_id=None
        command_part=shlex.split(message)
        client_ip=ast.literal_eval(command_part[len(command_part)-1])
        client_address=client_ip[0]
        try:
            client_socket=self.clients[client_ip]["socket"]
        except:
            print("ErrorWhileSerchingClientSocket: can not find the client socket, file sending failed")
            traceback.print_exc()
            return False
        print(client_socket, client_address, message)
        with self.file_client_id_lock:
            client_id=copy.copy(self.file_client_id)
            send_msg=message.strip()+" "+str(self.file_client_id)+"\n"
            self.file_client_id+=1
        try:
            waiting_time=0
            if shlex.split(message.lower())[0]=="/file_folder":
                filename=os.path.join(
                    file_folder_abspath, shlex.split(message)[2])
            else:
                filename = shlex.split(message)[1]
            self.send_message(client_socket, send_msg)
            file_transfer_client_port=self.palloc()
            file_server_port=None
            is_find_port=True
            while is_find_port:
                time.sleep(1)
                if len(self.file_server_port_list)>0:
                    with self.file_transfer_server_port_lock:
                        for port_info in self.file_server_port_list:
                            if port_info[1]==client_id:
                                file_server_port=port_info[0]
                                self.file_server_port_list.remove(port_info)
                                is_find_port=False
                                break
                    pass
                waiting_time+=1
                if waiting_time>=20:
                    print(
                        "ErrorWhileRecieveFileServerPort: transfer port waitting timeout, file sending failed")
                    return False
            self.file_transfer_mode(filename, client_address, file_server_port,
                                    file_transfer_client_port)
            self.pfree(file_transfer_client_port)
        except IndexError:
            print("invalid command, please use '/file <filename>'")
            traceback.print_exc()
    def file_transfer_mode(self, filename, server_address, server_port, client_port):
        print(f"start to send file: {filename}")
        client_file_socket = None
        reset_time=0
        def close_socket():
            nonlocal file_running
            nonlocal client_file_socket
            file_running = False
            client_file_socket.close()
            with self.file_client_id_lock:
                self.file_client_id-=1
        while True:
            try:
                client_file_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                client_file_socket.bind((self.host, client_port))
                client_file_socket.connect((server_address, server_port))
                break
            except Exception as e:
                print(f"file transfer connection error: {e}")
                traceback.print_exc()
                if reset_time >= 20:
                    close_socket()
                    print("unable to connect to file transfer server, file sending failed")
                    return False
                reset_time += 1
                time.sleep(1)
        file_running = True
        file_receive_data_from_server=""
        def receive_file_transfer_messages():
            nonlocal file_running
            nonlocal client_file_socket
            nonlocal file_receive_data_from_server
            while file_running:
                try:
                    data = self.recieve_message(
                        client_file_socket, 4096)
                    if not data:
                        print("\nbreak the file transfer connection from server")
                        try:
                            self.send_message(client_file_socket,
                                              self.error_sign)
                        except:
                            traceback.print_exc()
                            pass
                        close_socket()
                        break
                    file_receive_data_from_server=(
                        data.decode('utf-8').strip())
                    if file_receive_data_from_server==self.error_sign:
                        print("\nError sign received from server, file transfer may have failed")
                        close_socket()
                        break
                except Exception as e:
                    print(f"\nget file transfer msg error: {e}")
                    traceback.print_exc()
                    try:
                        self.send_message(client_file_socket,
                                          self.error_sign)
                    except:
                        traceback.print_exc()
                        pass
                    close_socket()
                    break
        receive_thread = threading.Thread(
            target=receive_file_transfer_messages, daemon=True)
        receive_thread.start()
        waiting_time = 0
        try:
            while True:
                if (file_receive_data_from_server ==
                    self.server_start_file_transfer_sign):
                    break
                if (file_receive_data_from_server ==
                    self.error_sign):
                    close_socket()
                    break
                time.sleep(1)
                waiting_time += 1
                if waiting_time >= 10:
                    try:
                        self.send_message(client_file_socket,
                                          self.error_sign)
                    except:
                        traceback.print_exc()
                        pass
                    print(f"ErrorWhileSendFile: \
                          Wait file transfer function start sign timeout, \
                          file {filename} sending failed")
                    close_socket()
                    return False
            waiting_time = 0
            file_size = os.path.getsize(filename)
            file_name_encoded = filename.encode('utf-8')
            name_len = len(file_name_encoded)
            self.send_message(client_file_socket, name_len.to_bytes(4, 'big'))
            self.send_message(client_file_socket, file_name_encoded)
            self.send_message(client_file_socket, file_size.to_bytes(8, 'big'))
            with open(filename, 'rb') as f:
                while True:
                    file_data = f.read(65536)
                    if not file_data:
                        break
                    self.send_message(client_file_socket, file_data)
            extra_time = (file_size // (100 * 1024 * 1024)) * 10
            timeout = int(30 + extra_time)
            while True:
                if (file_receive_data_from_server ==
                    self.server_reseived_file_data_sign):
                    break
                if (file_receive_data_from_server ==
                    self.error_sign):
                    close_socket()
                    break
                time.sleep(1)
                waiting_time += 1
                if waiting_time >= timeout:
                    try:
                        self.send_message(client_file_socket,
                                          self.error_sign)
                    except:
                        traceback.print_exc()
                        pass
                    close_socket()
                    print(f"ErrorWhileSendFileData: \
                          wait file transfer confirmation sign timeout, \
                          file {filename} sending may have failed")
                    return False
            print(f"Success: file {filename} sent successfully")
            close_socket()
            return True
        except FileNotFoundError:
            traceback.print_exc()
            try:
                self.send_message(client_file_socket,
                                  self.error_sign)
            except:
                traceback.print_exc()
                pass
            close_socket()
            print(f"file {filename} not exist")
            return False
        except Exception as e:
            traceback.print_exc()
            try:
                self.send_message(client_file_socket,
                                  self.error_sign)
            except:
                traceback.print_exc()
                pass
            close_socket()
            print(f"send error: {e}")
            return False
    def start_TCP_Server(self):  # set up server socket
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_clients)
            self.running = True
            print(f"TCP server deployed on {self.host}:{self.port}")
            print(f"max clients mount: {self.max_clients}")
            print("input '/stop' to stop the server\n")
            if self.is_input_command_in_console:
                input_thread = threading.Thread(
                    target=self.console_input, daemon=True)  # set up console input thread
                input_thread.start()
            else:
                pass
            while self.running:  # main loop to accept clients
                try:
                    client_socket, client_address = self.server_socket.accept()
                    if len(self.clients) >= self.max_clients:
                        self.send_message(client_socket,
                                          "Max connection mount, try latter")
                        client_socket.close()
                        continue
                    client_thread = threading.Thread(  # set up client handling thread
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True)
                    client_thread.start()
                except OSError:
                    traceback.print_exc()
                    break  # server socket closed, exit loop
        except Exception as e:
            print(f"Server error: {e}")
            traceback.print_exc()
        finally:
            self.stop()
    def console_input(self):  # deal consule input
        while self.running:
            try:
                cmd = input()
                deal_cmd = cmd.lower().strip()
                if deal_cmd == '/stop':
                    print("shutting down...")
                    self.running = False
                    self.stop()
                elif deal_cmd == '/status':
                    print(f"current connection count: {len(self.clients)}")
                    print(f"server running: {self.running}")
                elif deal_cmd == '/clients':
                    with self.client_lock:
                        for addr, info in self.clients.items():
                            print(f"  {info['id']} - connection time: {info['connected_time']}")
                elif shlex.split(deal_cmd)[0] == '/send_msg':
                    self.send_msg_to_specific_client(deal_cmd)
                elif shlex.split(deal_cmd)[0] == '/file':
                    self.file_transfer_server_recv_client_start_thread(
                        deal_cmd)
                elif shlex.split(deal_cmd)[0] == '/file_folder':
                    self.folder_file_transfer_server_recv_client_start(
                        deal_cmd)
                elif shlex.split(deal_cmd)[0] == '/multiple_file_multiple_client':
                    self.multiple_file_multiple_client_transfer_server_recv_client_start(
                        deal_cmd)
                elif shlex.split(deal_cmd)[0] == '/diff_multiple_file_diff_multiple_client':
                    self.diff_multiple_file_diff_multiple_client_transfer_server_recv_client_start(
                        deal_cmd)
                elif shlex.split(deal_cmd)[0] == '/help':
                    help_text=["avalable commands:",
                                "/stop - stop the server\n",
                                "\t/status - display server status\n",
                                "\t/clients - display connected clients\n",
                                "\t/send_msg <message1> <message2> ... ",
                                "<client_id1> <client_id2> ... <messageN>",
                                " ... <client_idN> ... - send message or ",
                                "messages to specific client or clients\n",
                                "\t/file <file_path> <client_id> - ",
                                "send file to specific client\n",
                                "\t/file_folder <folder_path> <client_id> - ",
                                "send folder to specific client\n",
                                "\t/multiple_file_multiple_client <file1> <file2>",
                                " ... <client_id1> <client_id2> ... <fileN> ...",
                                " <client_idN> ... - send multiple files to multiple",
                                " clients, files should be before clients, ",
                                "and clients should be in format of (ip, port)\n",
                                "\t/diff_multiple_file_diff_multiple_client <file1> <file2>",
                                " ... <client_id1> <client_id2> ... <fileN> ...",
                                " <client_idN> ... - send multiple files to multiple clients",
                                " with different file list for each client, files and clients",
                                " should be in pairs, and clients should be in format of (ip, port)"]
                    print("\n"+" ".join(help_text)+"\n")
                else:
                    cmd_parts = shlex.split(deal_cmd)
                    if not cmd_parts:
                        return None
                    cmd_name = cmd_parts[0].lower()
                    if (cmd_name in self._custom_handlers[1]):
                        handler = self._custom_handlers[1][cmd_name]
                        run_in_thread = self._custom_handler_threaded[1].get(
                            cmd_name, False)
                        if run_in_thread:
                            self._custom_executor.submit(
                                self._execute_custom_handler, handler, deal_cmd)
                            return "Command received, processing in background.\n"
                        else:
                            response = self._execute_custom_handler(
                                handler, deal_cmd)
                            return response
                    else:
                        print("Unrecognized command, input '/help' for available commands")
            except:
                traceback.print_exc()
                break
    def stop(self):  # shutting down the server
        self.running = False
        self.free_port()
        with self.client_lock:  # close all clients connections
            for client_info in self.clients.values():
                try:
                    client_info['socket'].close()
                except:
                    traceback.print_exc()
                    pass
            self.clients.clear()
        if self.server_socket:  # close server socket
            self.server_socket.close()
            print("server stopped")
class TCP_Client_Base:  # TCP client class
    def __init__(self, host=None, client_host='127.0.0.1',
                 port=65432, client_port=None, timeout=None,
                 port_add_step=1, max_thread_num=10,
                 is_input_command_in_console=True, is_wait_server=True,
                 max_custom_workers=10, is_extend_command=False):
        self.project_dir=os.path.dirname(os.path.abspath(__file__))
        self.file_transfer_dir=os.path.join(
            self.project_dir, 'received_files')
        self.decode_command_table_file_path=os.path.join(
            self.project_dir, 'decode_command_table.json')
        self.project_info_dir=os.path.join(self.project_dir, '.ServSpy')
        if os.path.exists(self.project_info_dir)==False:
            os.mkdir(self.project_info_dir)
        self.project_temp_info_dir=os.path.join(
            self.project_info_dir, 'temp_info')
        self.client_port_lock_file=os.path.join(
            self.project_temp_info_dir, 'client_port_lock.lock')
        if os.path.exists(self.project_temp_info_dir)==False:
            os.mkdir(self.project_temp_info_dir)
        self.all_alloced_ports_list=[]
        self.is_hand_alloc_port=None
        self.file_transfer_server_port=None
        self.file_server_port_list=[]
        self.file_transfer_server_port_lock=threading.Lock()
        self.client_ports_list=[]
        self.client_port=client_port
        self.host = host
        self.client_host = client_host
        self.port = port
        self.port_add_step=port_add_step
        self.latest_port=None
        self.timeout = timeout
        self.client_socket = None
        self.running = False
        self.receive_thread = None
        self.command_decode_table_str=None
        self.max_thread_num=max_thread_num
        self.is_input_command_in_console=is_input_command_in_console
        self.is_wait_server=is_wait_server
        if self.is_wait_server and self.timeout!=None:
            error_msg=["wait_server_timeout is not applicable when is_wait_server is True,",
                       "please set wait_server_timeout to None or set is_wait_server to False"]
            raise ValueError(" ".join(error_msg))
        self.file_client_id=0
        self.file_client_id_lock=threading.Lock()
        MAX_CONCURRENT_FILES = self.max_thread_num
        self.file_semaphore = threading.Semaphore(MAX_CONCURRENT_FILES)
        with open(self.decode_command_table_file_path, 'r', encoding='utf-8') as f:
            self.command_decode_table_str = f.read()
        self.command_decode_table=(
            ast.literal_eval(self.command_decode_table_str))
        self.send_file_header_sign = (
            self.command_decode_table[0]["file_send_server_header"])
        self.send_file_data_sign = (
            self.command_decode_table[0]["file_send_server_data"])
        self.server_reseived_file_header_sign = (
            self.command_decode_table[0]["file_resieve_client_header"])
        self.server_reseived_file_data_sign = (
            self.command_decode_table[0]["file_resieve_client_data"])
        self.server_start_file_transfer_sign = (
            self.command_decode_table[0]["file_send_server_start_file_transfer"])
        self.error_sign=(
            self.command_decode_table[0]["file_send_resieve_error"])
        self._custom_handlers = [{}, {}]
        self._custom_handler_threaded = [{}, {}]
        self._custom_executor = ThreadPoolExecutor(max_workers=max_custom_workers)
        self._task_semaphore = threading.Semaphore(max_custom_workers)
        self.is_extend_command=is_extend_command
        if self.is_extend_command:
            pass
        else:
            self.start_TCP_client()
    def register_command(self, command_name, handler, where_to_run, run_in_thread=False):
        registe_index=None
        if where_to_run=="server":
            registe_index=0
        elif where_to_run=="client":
            registe_index=1
        else:
            print(f"Invalid where_to_run value: {where_to_run}, must be 'server' or 'client'")
            return False
        self._custom_handlers[registe_index][command_name] = handler
        self._custom_handler_threaded[registe_index][command_name] = run_in_thread
    def submit_task(self, func, *args, **kwargs):
        self._task_semaphore.acquire()
        future = self._custom_executor.submit(func, *args, **kwargs)
        future.add_done_callback(lambda f: self._task_semaphore.release())
        return future
    def alloc_port(self, port_add_step, port_range_num):
        if self.is_hand_alloc_port==True:
            while self.is_client_port_temp_info_file_locked():
                time.sleep(0.1)
            self.client_port_temp_info_file_lock()
            self.hand_alloc_port(port_add_step, port_range_num)
            self.client_port_temp_info_file_unlock()
    def free_port(self):
        if self.is_hand_alloc_port==True:
            while self.is_client_port_temp_info_file_locked():
                time.sleep(0.1)
            self.client_port_temp_info_file_lock()
            self.hand_free_port()
            self.client_port_temp_info_file_unlock()
    def client_port_temp_info_file_lock(self):
        with open(self.client_port_lock_file, 'w', encoding='utf-8') as f:
            f.write("locked")
    def is_client_port_temp_info_file_locked(self):
        if os.path.exists(self.client_port_lock_file):
            return True
        else:
            return False
    def client_port_temp_info_file_unlock(self):
        if os.path.exists(self.client_port_lock_file):
            os.remove(self.client_port_lock_file)
    def hand_alloc_port(self, port_add_step, port_range_num):
        self.port_temp_info_path=os.path.join(
            self.project_temp_info_dir, 'clients_port_info.log')
        server_port_temp_info_file_path=os.path.join(
            self.project_temp_info_dir, 'server_port_info.log')
        if os.path.exists(server_port_temp_info_file_path)==True:
            print("Warning: server port info file exists, means the server has already allocated a port, may cause port conflict!")
        self.port_add_step = port_add_step
        self.port_range_num = port_range_num
        self.add_latest_port=self.port+1
        self.minus_latest_port=self.port
        self.alloc_add_port_lock=threading.Lock()
        self.alloc_minus_port_lock=threading.Lock()
        if os.path.exists(self.port_temp_info_path)==False:
            self.client_num=0
            self.client_port_info=[]
            self.min_port=self.port-self.port_add_step*self.port_range_num
            self.max_port=self.port+1+self.port_add_step*self.port_range_num
            each_client_info={
                "client_id": self.client_num,
                "host": self.host,
                "port": self.port,
                "min_port": self.min_port,
                "max_port": self.max_port,
                "is_running": self.running}
            self.client_port_info.append(each_client_info)
            with open(self.port_temp_info_path, 'w', encoding='utf-8') as f:
                f.write(str(self.client_port_info))
        else:
            with open(self.port_temp_info_path, 'r', encoding='utf-8') as f:
                self.client_port_info=ast.literal_eval(f.read())
            self.client_num=(
                self.client_port_info[len(self.client_port_info)-1]["client_id"]+1)
            auto_port_add=(
                self.client_port_info[len(self.client_port_info)-1]["max_port"]+
                self.port_add_step*self.port_range_num+1)
            auto_port_minus=(
                self.client_port_info[len(self.client_port_info)-1]["min_port"]-
                self.port_add_step*self.port_range_num-1)
            if self.port>auto_port_minus and self.port<auto_port_add:
                self.port=auto_port_add
            self.min_port=self.port-self.port_add_step*self.port_range_num
            self.max_port=self.port+1+self.port_add_step*self.port_range_num
            each_client_info={
                "client_id": self.client_num,
                "host": self.host,
                "port": self.port,
                "min_port": self.min_port,
                "max_port": self.max_port,
                "is_running": self.running}
            self.client_port_info.append(each_client_info)
            for is_running in range(len(self.client_port_info)-1, -1, -1):
                if self.client_port_info[is_running]["is_running"]==False:
                    del self.client_port_info[is_running]
            with open(self.port_temp_info_path, 'w', encoding='utf-8') as f:
                f.write(str(self.client_port_info))
    def hand_free_port(self):
        self.port_temp_info_path=os.path.join(
            self.project_temp_info_dir, 'clients_port_info.log')
        if os.path.exists(self.port_temp_info_path):
            with open(self.port_temp_info_path, 'r', encoding='utf-8') as f:
                self.client_port_info=ast.literal_eval(f.read())
            for client_num in range(len(self.client_port_info)):
                if self.client_port_info[client_num]["client_id"]==self.client_num:
                    del self.client_port_info[client_num]
            if len(self.client_port_info)==0:
                os.remove(self.port_temp_info_path)
            else:
                with open(self.port_temp_info_path, 'w', encoding='utf-8') as f:
                    f.write(str(self.client_port_info))
    def palloc(self):
        alloc_port=0
        while True:
            alloc_port=self.file_palloc()
            time.sleep(0.1)
            if alloc_port is not None:
                return alloc_port
            else:
                alloc_port=self.spy_palloc()
                if alloc_port is not None:
                    return alloc_port
                else:
                    pass
    def pfree(self, port):
        self.file_pfree(port)
        self.spy_pfree(port)
    def file_palloc(self):
        if self.is_hand_alloc_port:
            with self.alloc_add_port_lock:
                if self.add_latest_port + self.port_add_step > self.max_port:
                    for step in range(self.port+1, self.max_port, self.port_add_step):
                        if step in self.all_alloced_ports_list:
                            pass
                        else:
                            alloced_port=step
                            self.all_alloced_ports_list.append(alloced_port)
                            return alloced_port
                    return None
                self.add_latest_port += self.port_add_step
                self.all_alloced_ports_list.append(self.add_latest_port)
                return self.add_latest_port
        else:
            return 0
    def file_pfree(self, port):
        if self.is_hand_alloc_port:
            with self.alloc_add_port_lock:
                if port in self.all_alloced_ports_list:
                    self.all_alloced_ports_list.remove(port)
                    print(
                        "releasing file transfer port, current latest port:", port)
                self.add_latest_port-=self.port_add_step
        else:
            pass
    def spy_palloc(self):
        if self.is_hand_alloc_port:
            with self.alloc_minus_port_lock:
                if self.minus_latest_port - self.port_add_step < self.min_port:
                    for step in range(self.port, self.min_port, -self.port_add_step):
                        if step in self.all_alloced_ports_list:
                            pass
                        else:
                            alloced_port=step
                            self.all_alloced_ports_list.append(alloced_port)
                            return alloced_port
                    return None
                self.minus_latest_port -= self.port_add_step
                self.all_alloced_ports_list.append(self.minus_latest_port)
                return self.minus_latest_port
        else:
            return 0
    def spy_pfree(self, port):
        if self.is_hand_alloc_port:
            with self.alloc_minus_port_lock:
                if port in self.all_alloced_ports_list:
                    self.all_alloced_ports_list.remove(port)
                    print(
                        "releasing file transfer port, current latest port:", port)
                self.minus_latest_port+=self.port_add_step
        else:
            pass
    def create_temporary_server(self, handler, port=None, max_connections=1):
        if port is None:
            port = self.palloc()
            if port is None:
                raise RuntimeError("No available port for temporary server")
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.client_host, port))
        server_socket.listen(max_connections)
        stop_event = threading.Event()
        def server_loop():
            while not stop_event.is_set():
                try:
                    server_socket.settimeout(1.0)
                    client_sock, addr = server_socket.accept()
                    threading.Thread(target=handler,
                                     args=(client_sock, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if not stop_event.is_set():
                        print(f"Temporary server error: {e}")
                    break
            server_socket.close()
            self.pfree(port)
        server_thread = threading.Thread(target=server_loop, daemon=True)
        server_thread.start()
        return port, server_thread, stop_event
    def create_temporary_client(self, server_host, server_port, bind_port=None, on_data=None):
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if bind_port is not None:
            client_sock.bind((self.client_host, bind_port))
        else:
            bind_port = self.palloc()
            client_sock.bind((self.client_host, bind_port))
        client_sock.connect((server_host, server_port))
        stop_event = threading.Event()
        def receiver():
            while not stop_event.is_set():
                try:
                    client_sock.settimeout(1.0)
                    data = self.recieve_message(client_sock, 4096)
                    if not data:
                        break
                    if on_data:
                        on_data(data, client_sock)
                except socket.timeout:
                    continue
                except:
                    break
            client_sock.close()
        recv_thread = threading.Thread(target=receiver, daemon=True)
        recv_thread.start()
        return client_sock, recv_thread, stop_event
    def connect(self):  # connect to server
        while True:
            try:
                self.client_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                if self.timeout!=None:
                    self.client_socket.settimeout(self.timeout)  # connect over 5 seconds timeout
                else:
                    self.client_socket.settimeout(5)
                print(f"connecting to {self.host}:{self.port}...")
                if self.client_port==None:
                    pass
                else:
                    self.local_address=(self.client_host, self.client_port)
                    self.client_socket.bind(self.local_address)
                self.client_socket.connect((self.host, self.port))
                self.running = True
                self.receive_thread = threading.Thread(target=self.receive_messages)  # set up get msg thread
                self.receive_thread.daemon = True
                self.receive_thread.start()
                print("connect success! type '/help' to get help.\n")
                return True
            except socket.timeout:
                if self.is_wait_server:
                    print("waitting for server to start...")
                    pass
                else:
                    print("outof time, unable to connect to server")
                    traceback.print_exc()
                    return False
            except ConnectionRefusedError:
                if self.is_wait_server:
                    print("waitting for server to start...")
                    pass
                else:
                    print("connection rejected by server, please ensure the server is running")
                    traceback.print_exc()
                    return False
            except Exception as e:
                print(f"connection error: {e}")
                traceback.print_exc()
                return False
    def receive_messages(self):  # get server msg
        buffer = ""
        while self.running:
            try:
                data = self.recieve_message(
                    self.client_socket, 4096)
                if not data:
                    print("\nbreak the connection from server")
                    self.running = False
                    self.free_port()
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:  # deal with multiple messages in buffer
                    line, buffer = buffer.split('\n', 1)
                    message=line.strip()
                    if not message:
                        continue
                    if message.startswith("/"):
                        self.handle_server_command(message)
                    if message:
                        print(f"\n[server] {line}")
            except socket.timeout:
                continue
            except ConnectionResetError:
                print("\nReset by server, connection closed")
                traceback.print_exc()
                self.running = False
                self.free_port()
                break
            except Exception as e:
                print(f"\nget msg error: {e}")
                traceback.print_exc()
                self.running = False
                self.free_port()
                break
    def send_message(self, client_socket, message):  # send msg to server
        if not self.running or not self.client_socket:
            print("disable the connect to server")
            return False
        try:  # add newline character for server to distinguish messages
            if isinstance(message, str):
                deal_msg = message.strip()
                if not deal_msg.endswith('\n'):
                    deal_msg += '\n'
                data = deal_msg.encode('utf-8')
            elif isinstance(message, bytes):
                data = message
            else:
                print(f"Unsupported message type: {type(message)}")
                return False
            client_socket.sendall(data)
            return True
        except Exception as e:
            print(f"send msg error: {e}")
            traceback.print_exc()
            return False
    def recieve_message(self, client_socket, msg_length):  # receive msg
        data=client_socket.recv(msg_length)
        return data
    def handle_server_command(self, command):  # deal with special command from server
        client_id = f"{self.client_host}:{self.client_port}"
        if command.lower().split(" ")[0] == "/client_alloc_port_range":
            if command.lower().split(" ")[1]=="no_limit":
                self.is_hand_alloc_port=False
                print("server has no limit on client port allocation")
            else:
                self.is_hand_alloc_port=True
                self.each_client_port_range=int(command.split(" ")[1])
                self.alloc_port(
                    self.port_add_step, self.each_client_port_range)
                print(f"server allocated port range for each client: {self.each_client_port_range}")
        elif command.lower().split(" ")[0] == "/server_file_transfer_port":
            with self.file_transfer_server_port_lock:
                self.file_transfer_server_port=int(command.split(" ")[1])
                try:
                    file_client_id=int(command.split(" ")[2])
                    self.file_server_port_list.append(
                        [self.file_transfer_server_port, file_client_id])
                except:
                    traceback.print_exc()
                    pass
        elif shlex.split(command.lower())[0] == "/file":
            self.file_transfer_client_recv_server_start_thread(
                client_id, self.client_socket, command)
        elif shlex.split(command.lower())[0] == "/file_folder":
            self.file_folder_transfer_client_recv_server_start_thread(
                command, client_id, self.client_socket)
        else:
            cmd_parts = shlex.split(command.strip())
            if not cmd_parts:
                return
            cmd_name = cmd_parts[0].lower()
            if cmd_name in self._custom_handlers[0]:
                handler = self._custom_handlers[0][cmd_name]
                run_in_thread = self._custom_handler_threaded[0].get(
                    cmd_name, False)
                if run_in_thread:
                    self.submit_task(self._execute_custom_handler,
                                    handler, command, self.client_socket, client_id)
                else:
                    self._execute_custom_handler(
                        handler, command, self.client_socket, client_id)
            else:
                print(f"Unknown server command: {command}")
    def _execute_custom_handler(self, handler, command, client_socket=None, client_address=None):
        try:
            result = handler(client_socket, client_address, command)
            if result is not None:
                if isinstance(result, str) and not result.endswith('\n'):
                    result += '\n'
                try:
                    self.send_message(client_socket, result)
                except Exception as e:
                    print(f"Error sending message: {e}")
                return result
            return None
        except Exception as e:
            error_msg = f"Error in custom command handler: {e}\n"
            traceback.print_exc()
            try:
                self.send_message(client_socket, error_msg)
            except Exception as e:
                print(f"Error sending error message: {e}")
            return error_msg
    def interactive_mode(self):  # Interactive mode
        client_id = f"{self.client_host}:{self.client_port}"
        try:
            while self.running:
                try:  # get user input
                    message = input()
                    if not self.running:
                        break
                    if message.strip():
                        if message.lower() == '/quit':
                            self.send_message(self.client_socket, '/quit')
                            time.sleep(0.5)
                            break
                        elif shlex.split(message.lower())[0]=="/file":
                            self.file_transfer_client_recv_client_start_thread(message)
                        elif shlex.split(message.lower())[0]=="/multiple_file":
                            self.multiple_file_transfer_client_recv_client_start(message)
                        elif shlex.split(message.lower())[0]=="/file_folder":
                            self.folder_file_transfer_client_recv_client_start(message)
                        elif shlex.split(message.lower())[0]=="/multiple_file_folder":
                            self.multiple_folder_file_transfer_client_recv_client_start(message)
                        else:
                            cmd_name = message[0].lower()
                            if cmd_name in self._custom_handlers[1]:
                                handler = self._custom_handlers[1][cmd_name]
                                run_in_thread = self._custom_handler_threaded[1].get(
                                    cmd_name, False)
                                if run_in_thread:
                                    self.submit_task(self._execute_custom_handler,
                                                    handler, message, self.client_socket, client_id)
                                else:
                                    self._execute_custom_handler(
                                        handler, message, self.client_socket, client_id)
                            else:
                                self.send_message(self.client_socket, message)
                                print(f"Unknown server command: {message}")
                except KeyboardInterrupt:
                    print("\nshutting down...")
                    traceback.print_exc()
                    self.send_message(self.client_socket, '/quit')
                    time.sleep(0.5)
                    break
                except EOFError:
                    traceback.print_exc()
                    break
        finally:
            self.close()
    def multiple_folder_file_transfer_client_recv_client_start(self, message):
        transfer_folder_file_list=shlex.split(message)[1:]
        for transfer_folder_file in transfer_folder_file_list:
            command="/file_folder {}".format(shlex.quote(transfer_folder_file))
            folder_file_transfer_client_recv_client_start_thread=(
                threading.Thread(
                target=self.folder_file_transfer_client_recv_client_start,
                args=(command, ),
                daemon=True))
            folder_file_transfer_client_recv_client_start_thread.start()
    def folder_file_transfer_client_recv_client_start(self, message):
        folder_path=shlex.split(message)[1]
        if os.path.isdir(folder_path)==False:
            print(f"{folder_path} is not a valid folder path")
            return False
        base_path=os.path.dirname(folder_path)
        def get_relative_path(base_path, abs_path):
            base = os.path.normpath(base_path)
            abs_ = os.path.normpath(abs_path)
            common = os.path.commonpath([base, abs_])
            if common != base:
                raise ValueError(f"'{abs_path}' is not a subpath of '{base_path}'")
            rel = os.path.relpath(abs_, base)
            if rel == '.':
                return ''
            rel = rel.replace(os.sep, '/')
            return '/' + rel
        def send_folder_transfer_command(folder_path, file_name=None, abspath=None):
            folder_transfer_command_message=(
                "/file_folder {}".format(shlex.quote(folder_path)))
            if file_name:
                each_file_transfer_command_message=(
                    "/file_folder {} {}".format(
                        shlex.quote(folder_path), shlex.quote(file_name)))
                self.file_transfer_client_recv_client_start_thread(
                    each_file_transfer_command_message, abspath)
                print(f"start to send folder command: {each_file_transfer_command_message}")
            else:
                self.send_message(self.client_socket, folder_transfer_command_message.strip())
                print(f"start to send folder command: {folder_transfer_command_message}")
        def start_file_transfer_with_limit(rel_dir, file, root):
            cmd = f"/file_folder {shlex.quote(rel_dir)} {shlex.quote(file)}"
            def limited_transfer():
                self.file_semaphore.acquire()
                try:
                    self.file_transfer_client_recv_client_start(cmd, root)
                finally:
                    self.file_semaphore.release()
            thread = threading.Thread(target=limited_transfer, daemon=True)
            thread.start()
            print(f"start to send file: {cmd} (limit {self.max_thread_num})")
        def get_all_files_in_folder():
            for root, dirs, files in os.walk(folder_path):
                rel_dir = get_relative_path(base_path, root)
                if root != folder_path:
                    send_folder_transfer_command(rel_dir)
                for file in files:
                    start_file_transfer_with_limit(rel_dir, file, root)
            print(f"finished sending all files in folder {folder_path}")
        transfer_path=get_relative_path(base_path, folder_path)
        send_folder_transfer_command(transfer_path)
        get_all_files_in_folder()
    def multiple_file_transfer_client_recv_client_start(self, message):
        file_list=shlex.split(message)[1:]
        for file in file_list:
            self.file_semaphore.acquire()
            try:
                each_file_transfer_command_message=(
                    "/file {}".format(shlex.quote(file)))
                self.file_transfer_client_recv_client_start_thread(
                    each_file_transfer_command_message)
                print(f"start to send file command: {each_file_transfer_command_message}")
            finally:
                self.file_semaphore.release()
    def file_transfer_client_recv_client_start_thread(self, message, file_folder_abspath=None):
        file_transfer_client_recv_client_start_thread=(
            threading.Thread(
            target=self.file_transfer_client_recv_client_start,
            args=(message, file_folder_abspath),
            daemon=True))
        file_transfer_client_recv_client_start_thread.start()
    def file_transfer_client_recv_client_start(self, message, file_folder_abspath):
        client_id=None
        with self.file_client_id_lock:
            client_id=copy.copy(self.file_client_id)
            send_msg=message.strip()+" "+str(self.file_client_id)
            self.file_client_id+=1
        try:
            waiting_time=0
            if shlex.split(message.lower())[0]=="/file_folder":
                filename=os.path.join(
                    file_folder_abspath, shlex.split(message)[2])
            else:
                filename = shlex.split(message)[1]
            self.send_message(self.client_socket, send_msg)
            file_transfer_client_port=self.palloc()
            file_server_port=None
            is_find_port=True
            while is_find_port:
                time.sleep(1)
                if len(self.file_server_port_list)>0:
                    with self.file_transfer_server_port_lock:
                        for port_info in self.file_server_port_list:
                            if port_info[1]==client_id:
                                file_server_port=port_info[0]
                                self.file_server_port_list.remove(port_info)
                                is_find_port=False
                                break
                    pass
                waiting_time+=1
                if waiting_time>=20:
                    print(
                        "ErrorWhileRecieveFileServerPort: transfer port waitting timeout, file sending failed")
                    return False
            self.file_transfer_mode(filename, self.host,
                                    file_server_port,
                                    file_transfer_client_port)
            self.pfree(file_transfer_client_port)
        except IndexError:
            traceback.print_exc()
            print("invalid command, please use '/file <filename>'")
    def file_transfer_mode(self, filename, server_address, server_port, client_port):
        print(f"start to send file: {filename}")
        client_file_socket = None
        reset_time=0
        def close_socket():
            nonlocal file_running
            nonlocal client_file_socket
            file_running = False
            client_file_socket.close()
            with self.file_client_id_lock:
                self.file_client_id-=1
        while True:
            try:
                client_file_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                client_file_socket.bind((self.client_host, client_port))
                client_file_socket.connect((server_address, server_port))
                break
            except Exception as e:
                print(f"file transfer connection error: {e}")
                traceback.print_exc()
                if reset_time >= 20:
                    close_socket()
                    print("unable to connect to file transfer server, file sending failed")
                    return False
                reset_time += 1
                time.sleep(1)
        file_running = True
        file_receive_data_from_server=""
        def receive_file_transfer_messages():
            nonlocal file_running
            nonlocal client_file_socket
            nonlocal file_receive_data_from_server
            while file_running:
                try:
                    data = self.recieve_message(client_file_socket, 4096)
                    if not data:
                        print("\nbreak the file transfer connection from server")
                        try:
                            self.send_message(client_file_socket, self.error_sign)
                        except:
                            traceback.print_exc()
                            pass
                        close_socket()
                        break
                    file_receive_data_from_server=(
                        data.decode('utf-8').strip())
                    if file_receive_data_from_server==self.error_sign:
                        print("\nError sign received from server, file transfer may have failed")
                        close_socket()
                        break
                except Exception as e:
                    print(f"\nget file transfer msg error: {e}")
                    traceback.print_exc()
                    try:
                        self.send_message(client_file_socket, self.error_sign)
                    except:
                        traceback.print_exc()
                        pass
                    close_socket()
                    break
        receive_thread = threading.Thread(
            target=receive_file_transfer_messages, daemon=True)
        receive_thread.start()
        waiting_time = 0
        try:
            while True:
                if (file_receive_data_from_server ==
                    self.server_start_file_transfer_sign):
                    break
                if (file_receive_data_from_server ==
                    self.error_sign):
                    close_socket()
                    break
                time.sleep(1)
                waiting_time += 1
                if waiting_time >= 10:
                    try:
                        self.send_message(client_file_socket, self.error_sign)
                    except:
                        traceback.print_exc()
                        pass
                    print(f"ErrorWhileSendFile: \
                          Wait file transfer function start sign timeout, \
                          file {filename} sending failed")
                    close_socket()
                    return False
            waiting_time = 0
            file_size = os.path.getsize(filename)
            file_name_encoded = filename.encode('utf-8')
            name_len = len(file_name_encoded)
            self.send_message(client_file_socket, name_len.to_bytes(4, 'big'))
            self.send_message(client_file_socket, file_name_encoded)
            self.send_message(client_file_socket, file_size.to_bytes(8, 'big'))
            with open(filename, 'rb') as f:
                while True:
                    file_data = f.read(65536)
                    if not file_data:
                        break
                    self.send_message(client_file_socket, file_data)
            extra_time = (file_size // (100 * 1024 * 1024)) * 10
            timeout = int(30 + extra_time)
            while True:
                if (file_receive_data_from_server ==
                    self.server_reseived_file_data_sign):
                    break
                if (file_receive_data_from_server ==
                    self.error_sign):
                    close_socket()
                    break
                time.sleep(1)
                waiting_time += 1
                if waiting_time >= timeout:
                    try:
                        self.send_message(client_file_socket, self.error_sign)
                    except:
                        traceback.print_exc()
                        pass
                    close_socket()
                    print(f"ErrorWhileSendFileData: \
                          wait file transfer confirmation sign timeout, \
                          file {filename} sending may have failed")
                    return False
            print(f"Success: file {filename} sent successfully")
            close_socket()
            return True
        except FileNotFoundError:
            traceback.print_exc()
            try:
                self.send_message(client_file_socket, self.error_sign)
            except:
                traceback.print_exc()
                pass
            close_socket()
            print(f"file {filename} not exist")
            return False
        except Exception as e:
            traceback.print_exc()
            try:
                self.send_message(client_file_socket, self.error_sign)
            except:
                traceback.print_exc()
                pass
            close_socket()
            print(f"send error: {e}")
            return False
    def file_folder_transfer_client_recv_server_start_thread(
            self, command, client_id, client_socket):
        relative_folder_path=shlex.split(command)[1]
        try:
            file_name=shlex.split(command)[2]
            folder_transfer_client_recv_server_start_thread=threading.Thread(
                target=self.file_transfer_client_recv_server_start,
                args=(client_id, client_socket, command, relative_folder_path, file_name),
                daemon=True)
            folder_transfer_client_recv_server_start_thread.start()
        except:
            folder_transfer_client_recv_server_start_thread=threading.Thread(
                target=self.file_transfer_client_recv_server_start,
                args=(client_id, client_socket, command, relative_folder_path),
                daemon=True)
            folder_transfer_client_recv_server_start_thread.start()
    def file_transfer_client_recv_server_start_thread(
            self, client_id, client_socket, command):
        file_transfer_client_recv_server_start_thread=threading.Thread(
                target=self.file_transfer_client_recv_server_start,
                args=(client_id, client_socket, command),
                daemon=True)
        file_transfer_client_recv_server_start_thread.start()
    def file_transfer_client_recv_server_start(
            self, client_id, client_socket, command, new_save_path=None, file_name=None):
        file_transfer_server_port=self.palloc()
        self.file_transfer_mode_recv(
            self.host, file_transfer_server_port,
            client_socket, client_id, new_save_path, file_name, command)
        self.pfree(file_transfer_server_port)
    def file_transfer_mode_recv(self, server_file_address, server_file_port,
                                client_socket, client_id, new_save_path, file_name, command):
        file_running=True
        client_file_socket=None
        server_file_socket=None
        save_path=None
        def close_socket():
            nonlocal file_running
            nonlocal client_file_socket
            nonlocal server_file_socket
            file_running=False
            client_file_socket.close()
            server_file_socket.close()
        def setting_file_save_path():
            nonlocal save_path
            save_path = self.file_transfer_dir
            if new_save_path:
                path_list=new_save_path.split("/")
                del path_list[0]
                for node in path_list:
                    save_path = os.path.join(save_path, node)
                    os.makedirs(save_path, exist_ok=True)
            if file_name or new_save_path==None:
                return save_path
            close_socket()
            return None
        def file_transfer_client_recv(client_id):
            nonlocal file_running
            nonlocal client_file_socket
            nonlocal server_file_socket
            nonlocal save_path
            filename = None
            self.send_message(
                client_file_socket, self.server_start_file_transfer_sign)
            try:
                name_len_bytes = b''
                while len(name_len_bytes) < 4:
                    chunk = self.recieve_message(
                        client_file_socket, 4 - len(name_len_bytes))
                    print(chunk)
                    if not chunk:
                        try:
                            self.send_message(client_file_socket, self.error_sign)
                        except:
                            traceback.print_exc()
                            pass
                        close_socket()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileNameLength: client disconnected")
                    name_len_bytes += chunk
                    if (name_len_bytes.strip()==
                        self.error_sign.encode('utf-8')):
                        close_socket()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileNameLength: client reported error and disconnected")
                name_len = int.from_bytes(name_len_bytes, 'big')
                file_name_encoded = b''
                while len(file_name_encoded) < name_len:
                    chunk = self.recieve_message(
                        client_file_socket, name_len - len(file_name_encoded))
                    if not chunk:
                        try:
                            self.send_message(client_file_socket, self.error_sign)
                        except:
                            traceback.print_exc()
                            pass
                        close_socket()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileName: client disconnected")
                    file_name_encoded += chunk
                    if (file_name_encoded.strip()==
                        self.error_sign.encode('utf-8')):
                        close_socket()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileName: client reported error and disconnected")
                filename = file_name_encoded.decode('utf-8')
                filename = filename.strip()
                filename = os.path.basename(filename)
                size_bytes = b''
                while len(size_bytes) < 8:
                    chunk = self.recieve_message(
                        client_file_socket, 8 - len(size_bytes))
                    if not chunk:
                        try:
                            self.send_message(client_file_socket, self.error_sign)
                        except:
                            traceback.print_exc()
                            pass
                        close_socket()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileSize: client disconnected")
                    size_bytes += chunk
                    if (size_bytes.strip()==
                        self.error_sign.encode('utf-8')):
                        close_socket()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileSize: client reported error and disconnected")
                file_size = int.from_bytes(size_bytes, 'big')
                self.send_message(client_file_socket,
                                  self.server_reseived_file_header_sign)
                original_filename = filename
                if file_name:
                    final_filename = file_name.strip()
                else:
                    final_filename = os.path.basename(original_filename)
                full_path = os.path.join(save_path, final_filename).strip()
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path.strip(), 'wb') as f:
                    remaining = file_size
                    while remaining > 0:
                        chunk = self.recieve_message(
                            client_file_socket, min(65536, remaining))
                        if not chunk:
                            try:
                                self.send_message(client_file_socket,
                                    self.error_sign)
                            except:
                                traceback.print_exc()
                                pass
                            close_socket()
                            raise ConnectionError(
                                "ErrorWhileReceivingFileData: client disconnected")
                        f.write(chunk)
                        remaining -= len(chunk)
                self.send_message(client_file_socket,
                    self.server_reseived_file_data_sign)
                print(f"file {filename} received from {client_id}, size {file_size} bytes")
                close_socket()
            except Exception as e:
                traceback.print_exc()
                try:
                    self.send_message(client_file_socket,
                        self.error_sign)
                except:
                    traceback.print_exc()
                    pass
                close_socket()
                print(f"ErrorWhileReceiveFile: {e}")
                return False
            else:
                close_socket()
                return None
        server_file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_file_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_file_socket.bind((server_file_address, server_file_port))
        file_transfer_server_port=server_file_socket.getsockname()[1]
        command_part=shlex.split(command)
        file_client_id=command_part[len(command_part)-1]
        transfer_server_port_msg=(
            "/server_file_transfer_port {} {}\n".format(
                file_transfer_server_port, file_client_id))
        self.send_message(client_socket,
                          transfer_server_port_msg)
        server_file_socket.listen(1)
        try:
            client_file_socket, client_file_address = server_file_socket.accept()
            is_open_file_transfer=setting_file_save_path()
            if is_open_file_transfer==None:
                pass
            else:
                threading.Thread(
                    target=file_transfer_client_recv,
                    args=(client_id, ),
                    daemon=True).start()
        except Exception as e:
            print(f"\nget file transfer msg error: {e}")
            traceback.print_exc()
            close_socket()
        finally:
            server_file_socket.close()
    def close(self):  # close connection
        self.running = False
        self.free_port()
        if self.client_socket:
            self.client_socket.close()
        print("connection closed")
    def start_TCP_client(self):  # start client
        if not self.connect():
            sys.exit(1)
        try:
            if self.is_input_command_in_console:
                self.interactive_mode()
            else:
                pass
        except KeyboardInterrupt:
            print("\nclient shutting down...")
            traceback.print_exc()
        finally:
            self.close()

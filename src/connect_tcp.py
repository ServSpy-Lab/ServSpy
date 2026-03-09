import os
import ast
import sys
import time
import socket
import threading
from datetime import datetime
class TCPServer_Base:  # TCP server class
    def __init__(self, host='127.0.0.1', port=65432,
                 max_clients=10, port_add_step=1, port_range_num=100,
                 is_hand_alloc_port=False):
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
        self.alloc_port(port_add_step, port_range_num)
        self.server_socket = None
        self.clients = {}  # store client info
        self.running = False
        self.client_lock = threading.Lock()  # add the threading lock
        self.receive_data_from_client = ""
        self.command_decode_table_str=None
        with open(self.decode_command_table_file_path, 'r', encoding='utf-8') as f:
            self.command_decode_table_str = f.read()
        self.command_decode_table=(
            ast.literal_eval(self.command_decode_table_str))
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
    def file_palloc(self):
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
    def file_pfree(self, port):
        with self.alloc_add_port_lock:
            if port in self.all_alloced_ports_list:
                self.all_alloced_ports_list.remove(port)
            self.add_latest_port-=self.port_add_step
    def spy_palloc(self):
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
    def spy_pfree(self, port):
        with self.alloc_minus_port_lock:
            if port in self.all_alloced_ports_list:
                self.all_alloced_ports_list.remove(port)
            self.minus_latest_port+=self.port_add_step
    def broadcast(self, message, exclude_client=None): # broadcast message to all clients except exclude_client
        with self.client_lock:
            disconnected_clients = []
            for addr, client_info in self.clients.items():
                if exclude_client and addr == exclude_client:
                    continue
                try:
                    client_info['socket'].sendall(message.encode('utf-8'))
                except:
                    disconnected_clients.append(addr)
            for addr in disconnected_clients:  # del disconnected clients
                if addr in self.clients:
                    print(f"deleting the disconnected client: {addr}")
                    self.clients[addr]['socket'].close()
                    del self.clients[addr]
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
        client_socket.sendall(welcome_msg.encode('utf-8'))
        if self.is_hand_alloc_port==True:
            broadcast_clients_port_alloc_range_msg="/client_alloc_port_range {}".format(
                self.each_client_port_range)
            self.broadcast(broadcast_clients_port_alloc_range_msg)
        else:
            broadcast_clients_port_alloc_range_msg="/client_alloc_port_range NO_LIMIT"
            self.broadcast(broadcast_clients_port_alloc_range_msg)
        print(self.clients)
        try:
            while True:
                data = client_socket.recv(4096)  # get msg from client
                print(data)
                if not data:
                    break
                message = data.decode('utf-8').strip()  # decode msg
                print(message)
                self.receive_data_from_client=message
                if message.startswith('/'):  # deal with special command
                    response = self.handle_command(
                        client_socket, client_address, message)
                else:
                    timestamp = datetime.now().strftime("%H:%M:%S")  # deal with normal message
                    log_msg = f"[{timestamp}] {client_id}: {message}"
                    print(log_msg)
                    response = f"msg send: {message}"
                if response:  # send response to client
                    client_socket.sendall(response.encode('utf-8'))
        except ConnectionResetError:
            print(f"client disconnected: {client_id}")
        except Exception as e:
            print(f"error while deal with client {client_id} : {e}")
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
            help_text = """
            avalable commands:
            /help - print help meg
            /time - display server time
            /clients - display connected clients
            /file - send file to server
            /quit - disconnect
            """
            send_str=help_text+"\n"
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
        elif command.lower().split(" ")[0] == "/file":
            file_transfer_client_recv_server_start_thread=threading.Thread(
                target=self.file_transfer_client_recv_server_start,
                args=(client_id, client_socket),
                daemon=True)
            file_transfer_client_recv_server_start_thread.start()
    def file_transfer_client_recv_server_start(self, client_id, client_socket):
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
        file_transfer_server_port=0
        if self.is_hand_alloc_port==True:
            while True:
                time.sleep(0.1)
                file_transfer_server_port=self.file_palloc()
                if file_transfer_server_port!=None:
                    break
        else:
            file_transfer_server_port=0
        self.file_transfer_mode_recv(
            self.host, file_transfer_server_port, client_socket, client_id)
        if self.is_hand_alloc_port==True:
            self.file_pfree(file_transfer_server_port)
            print(
                "releasing file transfer port, current latest port:", file_transfer_server_port)
    def file_transfer_mode_recv(self, server_file_address, server_file_port,
                                client_socket, client_id):
        file_running=True
        client_file_socket=None
        server_file_socket=None
        def close_socket():
            nonlocal file_running
            file_running=False
            client_file_socket.close()
            server_file_socket.close()
        def file_transfer_client_recv(client_id):
            nonlocal file_running
            nonlocal client_file_socket
            nonlocal server_file_socket
            filename = None
            client_file_socket.sendall(
                self.server_start_file_transfer_sign.encode('utf-8'))
            try:
                name_len_bytes = b''
                while len(name_len_bytes) < 4:
                    chunk = client_file_socket.recv(4 - len(name_len_bytes))
                    print(chunk)
                    if not chunk:
                        try:
                            client_file_socket.sendall(
                                self.error_sign.encode('utf-8'))
                        except:
                            pass
                        close_socket()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileNameLength: client disconnected")
                    name_len_bytes += chunk
                    if name_len_bytes == self.error_sign.encode('utf-8'):
                        close_socket()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileNameLength: client reported error and disconnected")
                name_len = int.from_bytes(name_len_bytes, 'big')
                file_name_encoded = b''
                while len(file_name_encoded) < name_len:
                    chunk = client_file_socket.recv(
                        name_len - len(file_name_encoded))
                    if not chunk:
                        try:
                            client_file_socket.sendall(
                                self.error_sign.encode('utf-8'))
                        except:
                            pass
                        close_socket()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileName: client disconnected")
                    file_name_encoded += chunk
                    if file_name_encoded == self.error_sign.encode('utf-8'):
                        close_socket()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileName: client reported error and disconnected")
                filename = file_name_encoded.decode('utf-8')
                filename = os.path.basename(filename)
                size_bytes = b''
                while len(size_bytes) < 8:
                    chunk = client_file_socket.recv(
                        8 - len(size_bytes))
                    if not chunk:
                        try:
                            client_file_socket.sendall(
                                self.error_sign.encode('utf-8'))
                        except:
                            pass
                        close_socket()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileSize: client disconnected")
                    size_bytes += chunk
                    if size_bytes == self.error_sign.encode('utf-8'):
                        close_socket()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileSize: client reported error and disconnected")
                file_size = int.from_bytes(size_bytes, 'big')
                client_file_socket.sendall(
                    self.server_reseived_file_header_sign.encode('utf-8'))
                save_path = os.path.join(self.file_transfer_dir, filename)
                os.makedirs(self.file_transfer_dir, exist_ok=True)
                with open(save_path, 'wb') as f:
                    remaining = file_size
                    while remaining > 0:
                        chunk = client_file_socket.recv(min(65536, remaining))
                        if not chunk:
                            try:
                                client_file_socket.sendall(
                                    self.error_sign.encode('utf-8'))
                            except:
                                pass
                            close_socket()
                            raise ConnectionError(
                                "ErrorWhileReceivingFileData: client disconnected")
                        f.write(chunk)
                        remaining -= len(chunk)
                client_file_socket.sendall(
                    self.server_reseived_file_data_sign.encode('utf-8'))
                print(f"file {filename} received from {client_id}, size {file_size} bytes")
                close_socket()
            except Exception as e:
                try:
                    client_file_socket.sendall(
                        self.error_sign.encode('utf-8'))
                except:
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
        transfer_server_port_msg=(
            "/server_file_transfer_port {}".format(file_transfer_server_port))
        client_socket.sendall(transfer_server_port_msg.encode('utf-8'))
        server_file_socket.listen(1)
        while file_running:
            try:
                client_file_socket, client_file_address = server_file_socket.accept()
                print(client_file_socket, client_file_address)
                threading.Thread(
                    target=file_transfer_client_recv,
                    args=(client_id, ),
                    daemon=True).start()
            except Exception as e:
                print(f"\nget file transfer msg error: {e}")
                break
            finally:
                server_file_socket.close()
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
            input_thread = threading.Thread(target=self.console_input, daemon=True)  # set up console input thread
            input_thread.start()
            while self.running:  # main loop to accept clients
                try:
                    client_socket, client_address = self.server_socket.accept()
                    if len(self.clients) >= self.max_clients:
                        client_socket.sendall("Max connection mount, try latter".encode('utf-8'))
                        client_socket.close()
                        continue
                    client_thread = threading.Thread(  # set up client handling thread
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True)
                    client_thread.start()
                except OSError:
                    break  # server socket closed, exit loop
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop()
    def console_input(self):  # deal consule input
        while self.running:
            try:
                deal_cmd=""
                cmd = list(input())
                del cmd[0]
                for i in range(len(cmd)):
                    deal_cmd += cmd[i]
                deal_cmd = deal_cmd.lower()
                if deal_cmd == 'stop':
                    print("shutting down...")
                    self.running = False
                    self.stop()
                elif deal_cmd == 'status':
                    print(f"current connection count: {len(self.clients)}")
                    print(f"server running: {self.running}")
                elif deal_cmd == 'clients':
                    with self.client_lock:
                        for addr, info in self.clients.items():
                            print(f"  {info['id']} - connection time: {info['connected_time']}")
                elif deal_cmd == 'file':
                    pass
            except:
                break
    def stop(self):  # shutting down the server
        self.running = False
        self.free_port()
        with self.client_lock:  # close all clients connections
            for client_info in self.clients.values():
                try:
                    client_info['socket'].close()
                except:
                    pass
            self.clients.clear()
        if self.server_socket:  # close server socket
            self.server_socket.close()
            print("server stopped")
class TCPClient_Base:  # TCP client class
    def __init__(self, host=None, client_host='127.0.0.1',
                 port=65432, client_ports=None, timeout=5, port_add_step=1):
        self.project_dir=os.path.dirname(os.path.abspath(__file__))
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
        self.client_ports=client_ports
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
        with open(self.decode_command_table_file_path, 'r', encoding='utf-8') as f:
            self.command_decode_table_str = f.read()
        self.command_decode_table=(
            ast.literal_eval(self.command_decode_table_str))
        self.start_TCP_client()
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
    def file_palloc(self):
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
    def file_pfree(self, port):
        with self.alloc_add_port_lock:
            if port in self.all_alloced_ports_list:
                self.all_alloced_ports_list.remove(port)
            self.add_latest_port-=self.port_add_step
    def spy_palloc(self):
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
    def spy_pfree(self, port):
        with self.alloc_minus_port_lock:
            if port in self.all_alloced_ports_list:
                self.all_alloced_ports_list.remove(port)
            self.minus_latest_port+=self.port_add_step
    def connect(self):  # connect to server
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(self.timeout)  # connect over 5 seconds timeout
            print(f"connecting to {self.host}:{self.port}...")
            if self.client_ports==None:
                pass
            else:
                self.local_address=(self.client_host, self.client_ports)
                self.client_socket.bind(self.local_address)
            self.client_socket.connect((self.host, self.port))
            self.running = True
            self.receive_thread = threading.Thread(target=self.receive_messages)  # set up get msg thread
            self.receive_thread.daemon = True
            self.receive_thread.start()
            print("connect success! type '/help' to get help.\n")
            return True
        except socket.timeout:
            print("outof time, unable to connect to server")
            return False
        except ConnectionRefusedError:
            print("connection rejected by server, please ensure the server is running")
            return False
        except Exception as e:
            print(f"connection error: {e}")
            return False
    def receive_messages(self):  # get server msg
        buffer = ""
        while self.running:
            try:
                data = self.client_socket.recv(4096)
                print(data)
                receive_data_from_server=data.decode('utf-8')
                print(receive_data_from_server)
                if receive_data_from_server.startswith("/"):
                    self.handle_server_command(receive_data_from_server)
                if not data:
                    print("\nbreak the connection from server")
                    self.running = False
                    self.free_port()
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:  # deal with multiple messages in buffer
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        print(f"\n[server] {line}")
            except socket.timeout:
                continue
            except ConnectionResetError:
                print("\nReset by server, connection closed")
                self.running = False
                self.free_port()
                break
            except Exception as e:
                print(f"\nget msg error: {e}")
                self.running = False
                self.free_port()
                break
    def send_message(self, message):  # send msg to server
        if not self.running or not self.client_socket:
            print("disable the connect to server")
            return False
        try:  # add newline character for server to distinguish messages
            if not message.endswith('\n'):
                message += '\n'
            self.client_socket.sendall(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"send msg error: {e}")
            return False
    def handle_server_command(self, command):  # deal with special command from server
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
                self.file_server_port_list.append(self.file_transfer_server_port)
    def interactive_mode(self):  # Interactive mode
        try:
            while self.running:
                try:  # get user input
                    message = input()
                    if not self.running:
                        break
                    if message.strip():
                        if message.lower() == '/quit':
                            self.send_message('/quit')
                            time.sleep(0.5)
                            break
                        elif message.lower().split(" ")[0]=="/file":
                            self.file_transfer_client_recv_client_start_thread(message)
                        elif message.lower().split(" ")[0]=="/multiple_file":
                            self.multiple_file_transfer_client_recv_client_start(message)
                        else:
                            self.send_message(message)
                except KeyboardInterrupt:
                    print("\nshutting down...")
                    self.send_message('/quit')
                    time.sleep(0.5)
                    break
                except EOFError:
                    break
        finally:
            self.close()
    def multiple_file_transfer_client_recv_client_start(self, message):
        file_list=message.split(" ")[1:]
        for file in file_list:
            each_file_transfer_command_message=(
                "/file {}".format(file))
            self.file_transfer_client_recv_client_start_thread(
                each_file_transfer_command_message)
            print(f"start to send file command: {each_file_transfer_command_message}")
    def file_transfer_client_recv_client_start_thread(self, message):
        file_transfer_client_recv_client_start_thread=(
            threading.Thread(
            target=self.file_transfer_client_recv_client_start,
            args=(message, ),
            daemon=True))
        file_transfer_client_recv_client_start_thread.start()
    def file_transfer_client_recv_client_start(self, message):
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
        send_msg=message
        while send_msg[len(send_msg)-1]==" ":
            send_msg=send_msg[:-1]
        try:
            waiting_time=0
            filename = message.split(" ")[1]
            self.send_message(send_msg)
            file_transfer_client_port=None
            if self.is_hand_alloc_port==True:
                file_transfer_client_port=self.file_palloc()
                if file_transfer_client_port==None:
                    while True:
                        time.sleep(0.1)
                        file_transfer_client_port=self.file_palloc()
                        if file_transfer_client_port!=None:
                            break
            else:
                file_transfer_client_port=0
            while True:
                time.sleep(0.1)
                if len(self.file_server_port_list)>0:
                    break
                waiting_time+=0.1
                if waiting_time>=10:
                    print(
                        "ErrorWhileRecieveFileServerPort: transfer port waitting timeout, file sending failed")
                    return False
            file_server_port=None
            with self.file_transfer_server_port_lock:
                file_server_port=(
                    self.file_server_port_list[len(self.file_server_port_list)-1])
                self.file_server_port_list.remove(file_server_port)
            self.file_transfer_mode(filename, self.host,
                                    file_server_port,
                                    file_transfer_client_port)
            if self.is_hand_alloc_port==True:
                self.file_pfree(file_transfer_client_port)
                print(
                    "releasing file transfer port, current latest port:", self.latest_port)
        except IndexError:
            print("invalid command, please use '/file <filename>'")
    def file_transfer_mode(self, filename, server_address, server_port, client_port):
        print(f"start to send file: {filename}")
        client_file_socket = None
        reset_time=0
        while True:
            try:
                client_file_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                client_file_socket.bind((self.client_host, client_port))
                client_file_socket.connect((server_address, server_port))
                break
            except Exception as e:
                print(f"file transfer connection error: {e}")
                if reset_time >= 20:
                    close_socket()
                    print("unable to connect to file transfer server, file sending failed")
                    return False
                reset_time += 1
                time.sleep(1)
        file_running = True
        file_receive_data_from_server=""
        def close_socket():
            nonlocal file_running
            nonlocal client_file_socket
            file_running = False
            client_file_socket.close()
        def receive_file_transfer_messages():
            nonlocal file_running
            nonlocal client_file_socket
            nonlocal file_receive_data_from_server
            while file_running:
                try:
                    data = client_file_socket.recv(4096)
                    if not data:
                        print("\nbreak the file transfer connection from server")
                        try:
                            client_file_socket.sendall(
                                self.error_sign.encode('utf-8'))
                        except:
                            pass
                        close_socket()
                        break
                    if data==self.error_sign.encode('utf-8'):
                        print("\nError sign received from server, file transfer may have failed")
                        close_socket()
                        break
                    file_receive_data_from_server=(
                        data.decode('utf-8').strip())
                except Exception as e:
                    print(f"\nget file transfer msg error: {e}")
                    try:
                        client_file_socket.sendall(
                            self.error_sign.encode('utf-8'))
                    except:
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
                        client_file_socket.sendall(
                            self.error_sign.encode('utf-8'))
                    except:
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
            client_file_socket.sendall(name_len.to_bytes(4, 'big'))
            client_file_socket.sendall(file_name_encoded)
            client_file_socket.sendall(file_size.to_bytes(8, 'big'))
            with open(filename, 'rb') as f:
                while True:
                    file_data = f.read(65536)
                    if not file_data:
                        break
                    client_file_socket.sendall(file_data)
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
                        client_file_socket.sendall(
                            self.error_sign.encode('utf-8'))
                    except:
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
            try:
                client_file_socket.sendall(
                    self.error_sign.encode('utf-8'))
            except:
                pass
            close_socket()
            print(f"file {filename} not exist")
            return False
        except Exception as e:
            try:
                client_file_socket.sendall(
                    self.error_sign.encode('utf-8'))
            except:
                pass
            close_socket()
            print(f"send error: {e}")
            return False
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
            self.interactive_mode()
        except KeyboardInterrupt:
            print("\nclient shutting down...")
        finally:
            self.close()

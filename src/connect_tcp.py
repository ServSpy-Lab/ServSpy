import os
import ast
import sys
import time
import socket
import threading
from datetime import datetime
class TCPServer_Base:  # TCP server class
    def __init__(self, host='127.0.0.1', port=65432, max_clients=10, port_add_step=1):
        self.project_dir=os.path.dirname(os.path.abspath(__file__))
        self.decode_command_table_file_path=os.path.join(
            self.project_dir, 'decode_command_table.json')
        self.file_transfer_dir=os.path.join(
            self.project_dir, 'received_files')
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.server_socket = None
        self.clients = {}  # store client info
        self.running = False
        self.client_lock = threading.Lock()  # add the threading lock
        self.file_running=None
        self.file_server_started = False
        self.file_server_lock = threading.Lock()  # lock for file server start
        self.receive_data_from_client = ""
        self.command_decode_table_str=None
        with open(self.decode_command_table_file_path, 'r', encoding='utf-8') as f:
            self.command_decode_table_str = f.read()
        self.command_decode_table=(
            ast.literal_eval(self.command_decode_table_str))
        self.start_TCP_Server()
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
                    print(111)
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
            self.file_transfer_client_recv_server_start(client_id, command)
    def file_transfer_client_recv_server_start(self, client_id, command):
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
        latest_port=None
        with self.file_server_lock:
            if not self.file_server_started:
                self.file_server_started = True
                latest_port=int(command.split(" ")[2])
                file_transfer_mode_recv_thread=threading.Thread(
                    target=self.file_transfer_mode_recv, 
                    args=(self.host, latest_port, client_id), 
                    daemon=True)
                file_transfer_mode_recv_thread.start()
            while True:
                # breakpoint()
                time.sleep(0.1)
                if self.file_server_started==False:
                    print(
                        "releasing file transfer port, current latest port:", latest_port-1)
                    file_transfer_mode_recv_thread.join()
                    break
    def file_transfer_mode_recv(self, server_file_address, server_file_port, client_id):
        self.file_running=True
        server_file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_file_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_file_socket.bind((server_file_address, server_file_port))
        server_file_socket.listen(1)
        while self.file_running:
            try:
                client_file_socket, client_file_address = server_file_socket.accept()
                threading.Thread(
                    target=self.file_transfer_client_recv, 
                    args=(client_file_socket, client_file_address, client_id), 
                    daemon=True).start()
            except Exception as e:
                self.file_server_started=False
                print(f"\nget file transfer msg error: {e}")
                break
        self.file_server_started=False
        print(self.file_server_started)
        server_file_socket.close()
    def file_transfer_client_recv(self, client_file_socket, client_file_address, client_id):
        filename = None
        client_file_socket.sendall(
            self.server_start_file_transfer_sign.encode('utf-8'))
        try:
            name_len_bytes = b''
            while len(name_len_bytes) < 4:
                chunk = client_file_socket.recv(4 - len(name_len_bytes))
                print(chunk)
                # breakpoint()
                if not chunk:
                    try:
                        client_file_socket.sendall(
                            self.error_sign.encode('utf-8'))
                    except:
                        pass
                    self.file_server_started=False
                    self.file_running=False
                    client_file_socket.close()
                    raise ConnectionError(
                        "ErrorWhileReceivingFileNameLength: client disconnected")
                name_len_bytes += chunk
                if (name_len_bytes == self.error_sign.encode('utf-8')):
                    self.file_server_started=False
                    self.file_running=False
                    client_file_socket.close()
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
                    self.file_server_started=False
                    self.file_running=False
                    client_file_socket.close()
                    raise ConnectionError(
                        "ErrorWhileReceivingFileName: client disconnected")
                file_name_encoded += chunk
                if (file_name_encoded == self.error_sign.encode('utf-8')):
                    self.file_server_started=False
                    self.file_running=False
                    client_file_socket.close()
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
                    self.file_server_started=False
                    self.file_running=False
                    client_file_socket.close()
                    raise ConnectionError(
                        "ErrorWhileReceivingFileSize: client disconnected")
                size_bytes += chunk
                if (size_bytes == self.error_sign.encode('utf-8')):
                    self.file_server_started=False
                    self.file_running=False
                    client_file_socket.close()
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
                        self.file_server_started=False
                        self.file_running=False
                        client_file_socket.close()
                        raise ConnectionError(
                            "ErrorWhileReceivingFileData: client disconnected")
                    if (chunk == self.error_sign.encode('utf-8')):
                        self.file_server_started=False
                        self.file_running=False
                        client_file_socket.close()
                        raise ConnectionError(
                            "ErrorSignReceivedWhileReceivingFileData: client reported error and disconnected")
                    f.write(chunk)
                    remaining -= len(chunk)
            client_file_socket.sendall(
                self.server_reseived_file_data_sign.encode('utf-8'))
            print(f"file {filename} received from {client_id}, size {file_size} bytes")
            self.file_server_started=False
            self.file_running=False
            client_file_socket.close()
        except Exception as e:
            try:
                client_file_socket.sendall(
                    self.error_sign.encode('utf-8'))
            except:
                pass
            self.file_server_started=False
            self.file_running=False
            client_file_socket.close()
            print(f"ErrorWhileReceiveFile: {e}")
            return False
        else:
            self.file_server_started=False
            self.file_running=False
            client_file_socket.close()
            return None
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
    def __init__(self, host='127.0.0.1', port=65432, timeout=5, port_add_step=1):
        self.file_transfer_port_lock=threading.Lock() # lock for file transfer port
        self.decode_command_table_file_path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'decode_command_table.json')
        self.file_transfer_mode_running=False
        self.host = host
        self.port = port
        self.port_add_step=port_add_step
        self.latest_port=self.port
        self.timeout = timeout
        self.client_socket = None
        self.running = False
        self.receive_thread = None
        self.receive_data_from_server = ""
        self.command_decode_table_str=None
        with open(self.decode_command_table_file_path, 'r', encoding='utf-8') as f:
            self.command_decode_table_str = f.read()
        self.command_decode_table=(
            ast.literal_eval(self.command_decode_table_str))
        self.start_TCP_client()
    def connect(self):  # connect to server
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(self.timeout)  # connect over 5 seconds timeout
            print(f"connecting to {self.host}:{self.port}...")
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
                self.receive_data_from_server=(
                    data.decode('utf-8').strip())
                if not data:
                    print("\nbreak the connection from server")
                    self.running = False
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
                break
            except Exception as e:
                print(f"\nget msg error: {e}")
                self.running = False
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
                            self.file_transfer_client_recv_client_start(message)
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
            filename = message.split(" ")[1]
            with self.file_transfer_port_lock:
                self.latest_port+= self.port_add_step
            self.send_message(send_msg+" "+str(self.latest_port))
            file_transfer_mode_thread=threading.Thread(
                    target=self.file_transfer_mode, 
                    args=(filename, self.host, self.latest_port), 
                    daemon=True)
            file_transfer_mode_thread.start()
            while True:
                time.sleep(0.1)
                if self.file_transfer_mode_running==False:
                    file_transfer_mode_thread.join()
                    with self.file_transfer_port_lock:
                        self.latest_port-=self.port_add_step
                    print(
                        "releasing file transfer port, current latest port:", self.latest_port)
                    break
        except IndexError:
            print("invalid command, please use '/file <filename>'")
    def file_transfer_mode(self, filename, server_address, server_port):
        self.file_transfer_mode_running=True
        print(f"start to send file: {filename}")
        self.client_file_socket = None
        reset_time=0
        while True:
            try:
                self.client_file_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                self.client_file_socket.connect((server_address, server_port))
                break
            except Exception as e:
                print(f"file transfer connection error: {e}")
                if reset_time >= 20:
                    self.client_file_socket.close()
                    self.file_transfer_mode_running=False
                    print("unable to connect to file transfer server, file sending failed")
                    return False
                reset_time += 1
                time.sleep(1)
        self.file_running=True
        self.file_receive_data_from_server=""
        def receive_file_transfer_messages():
            while self.file_running:
                try:
                    data = self.client_file_socket.recv(4096)
                    if not data:
                        print("\nbreak the file transfer connection from server")
                        self.file_running = False
                        try:
                            self.client_file_socket.sendall(
                                self.error_sign.encode('utf-8'))
                        except:
                            pass
                        self.client_file_socket.close()
                        self.file_transfer_mode_running=False
                        break
                    if data==self.error_sign.encode('utf-8'):
                        print("\nError sign received from server, file transfer may have failed")
                        self.file_running = False
                        self.client_file_socket.close()
                        self.file_transfer_mode_running=False
                        break
                    self.file_receive_data_from_server=(
                        data.decode('utf-8').strip())
                except Exception as e:
                    print(f"\nget file transfer msg error: {e}")
                    self.file_running = False
                    try:
                        self.client_file_socket.sendall(
                            self.error_sign.encode('utf-8'))
                    except:
                        pass
                    self.client_file_socket.close()
                    self.file_transfer_mode_running=False
                    break
        receive_thread = threading.Thread(
            target=receive_file_transfer_messages, daemon=True)
        receive_thread.start()
        waiting_time = 0
        try:
            while True:
                if (self.file_receive_data_from_server == 
                    self.server_start_file_transfer_sign):
                    break
                if (self.file_receive_data_from_server == 
                    self.error_sign):
                    self.file_running=False
                    self.client_file_socket.close()
                    self.file_transfer_mode_running=False
                    break
                time.sleep(1)
                waiting_time += 1
                if waiting_time >= 10:
                    try:
                        self.client_file_socket.sendall(
                            self.error_sign.encode('utf-8'))
                    except:
                        pass
                    self.file_running=False
                    self.client_file_socket.close()
                    print(f"ErrorWhileSendFile: \
                          Wait file transfer function start sign timeout, \
                          file {filename} sending failed")
                    self.file_transfer_mode_running=False
                    return False
            waiting_time = 0
            file_size = os.path.getsize(filename)
            file_name_encoded = filename.encode('utf-8')
            name_len = len(file_name_encoded)
            self.client_file_socket.sendall(name_len.to_bytes(4, 'big'))
            self.client_file_socket.sendall(file_name_encoded)
            self.client_file_socket.sendall(file_size.to_bytes(8, 'big'))
            with open(filename, 'rb') as f:
                while True:
                    file_data = f.read(65536)
                    if not file_data:
                        break
                    self.client_file_socket.sendall(file_data)
            extra_time = (file_size // (100 * 1024 * 1024)) * 10
            timeout = int(30 + extra_time)
            while True:
                if (self.file_receive_data_from_server == 
                    self.server_reseived_file_data_sign):
                    break
                if (self.file_receive_data_from_server == 
                    self.error_sign):
                    self.file_running=False
                    self.client_file_socket.close()
                    self.file_transfer_mode_running=False
                    break
                time.sleep(1)
                waiting_time += 1
                if waiting_time >= timeout:
                    try:
                        self.client_file_socket.sendall(
                            self.error_sign.encode('utf-8'))
                    except:
                        pass
                    self.file_running=False
                    self.client_file_socket.close()
                    print(f"ErrorWhileSendFileData: \
                          wait file transfer confirmation sign timeout, \
                          file {filename} sending may have failed")
                    self.file_transfer_mode_running=False
                    return False
            print(f"Success: file {filename} sent successfully")
            self.file_running=False
            self.client_file_socket.close()
            self.file_transfer_mode_running=False
            return True
        except FileNotFoundError:
            try:
                self.client_file_socket.sendall(
                    self.error_sign.encode('utf-8'))
            except:
                pass
            self.file_running=False
            self.client_file_socket.close()
            print(f"file {filename} not exist")
            self.file_transfer_mode_running=False
            return False
        except Exception as e:
            try:
                self.client_file_socket.sendall(
                    self.error_sign.encode('utf-8'))
            except:
                pass
            self.file_running=False
            self.client_file_socket.close()
            print(f"send error: {e}")
            self.file_transfer_mode_running=False
            return False
    def close(self):  # close connection
        self.running = False
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

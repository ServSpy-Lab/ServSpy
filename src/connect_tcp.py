import sys
import time
import socket
import threading
from datetime import datetime
class TCPServer_Base:
    def __init__(self, host='127.0.0.1', port=65432, max_clients=10):
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.server_socket = None
        self.clients = {}  # store client info
        self.running = False
        self.client_lock = threading.Lock()
        self.start_TCP_Server()
    def broadcast(self, message, exclude_client=None):
        """广播消息给所有客户端"""
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
                if not data:
                    break
                message = data.decode('utf-8').strip()  # decode msg
                if message.startswith('/'):  # deal with special command
                    response = self.handle_command(client_socket, client_address, message)
                else:
                    timestamp = datetime.now().strftime("%H:%M:%S")  # deal with normal message
                    log_msg = f"[{timestamp}] {client_id}: {message}"
                    print(log_msg)
                    broadcast_msg = f"[{timestamp}] client {client_id}: {message}"  # send broadcast message
                    self.broadcast(broadcast_msg, exclude_client=client_address)
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
        client_id = f"{client_address[0]}:{client_address[1]}"
        if command == '/help':
            help_text = """
            avalable commands:
            /help - print help meg
            /time - display server time
            /clients - display connected clients
            /quit - disconnect
            """
            return help_text
        elif command == '/time':
            return f"server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        elif command == '/clients':
            with self.client_lock:
                client_list = [info['id'] for info in self.clients.values()]
                return f"online clients ({len(client_list)}): {', '.join(client_list)}"
        elif command == '/quit':
            return "Bye!"
        else:
            return f"unknow: {command}"
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
                        args=(client_socket, client_address))
                    client_thread.daemon = True
                    client_thread.start()
                except OSError:
                    break  # server socket closed, exit loop
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop()
    def console_input(self):
        """处理控制台输入"""
        while self.running:
            try:
                cmd = input().strip().lower()
                if cmd == 'stop':
                    print("shutting down...")
                    self.running = False
                    self.stop()
                elif cmd == 'status':
                    print(f"current connection count: {len(self.clients)}")
                    print(f"server running: {self.running}")
                elif cmd == 'clients':
                    with self.client_lock:
                        for addr, info in self.clients.items():
                            print(f"  {info['id']} - connection time: {info['connected_time']}")
            except:
                break
                
    def stop(self):
        """停止服务器"""
        self.running = False
        
        # 关闭所有客户端连接
        with self.client_lock:
            for client_info in self.clients.values():
                try:
                    client_info['socket'].close()
                except:
                    pass
            self.clients.clear()
            
        # 关闭服务器套接字
        if self.server_socket:
            self.server_socket.close()
            print("server stopped")



class TCPClient_Base:
    def __init__(self, host='127.0.0.1', port=65432):
        self.host = host
        self.port = port
        self.client_socket = None
        self.running = False
        self.receive_thread = None
        
    def connect(self):
        """连接到服务器"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)  # 连接超时5秒
            
            print(f"connecting to {self.host}:{self.port}...")
            self.client_socket.connect((self.host, self.port))
            
            self.running = True
            
            # 启动接收消息线程
            self.receive_thread = threading.Thread(target=self.receive_messages)
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
            
    def receive_messages(self):
        """接收服务器消息"""
        buffer = ""
        while self.running:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    print("\nbreak the connection from server")
                    self.running = False
                    break
                    
                buffer += data.decode('utf-8')
                
                # 处理可能的分行消息
                while '\n' in buffer:
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
                
    def send_message(self, message):
        """发送消息到服务器"""
        if not self.running or not self.client_socket:
            print("disable the connect to server")
            return False
            
        try:
            # 添加换行符以便服务器区分消息
            if not message.endswith('\n'):
                message += '\n'
                
            self.client_socket.sendall(message.encode('utf-8'))
            return True
            
        except Exception as e:
            print(f"send msg error: {e}")
            return False
            
    def interactive_mode(self):
        """交互式模式"""
        try:
            while self.running:
                try:
                    # 获取用户输入
                    message = input()
                    
                    if not self.running:
                        break
                        
                    if message.strip():
                        if message.lower() == '/quit':
                            self.send_message('/quit')
                            time.sleep(0.5)
                            break
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
            
    def file_transfer_mode(self, filename):
        """文件传输模式（简单示例）"""
        try:
            with open(filename, 'rb') as file:
                # 发送文件名和大小
                file_data = file.read()
                header = f"/file {filename} {len(file_data)}\n"
                self.client_socket.sendall(header.encode('utf-8'))
                time.sleep(0.1)
                
                # 发送文件数据
                self.client_socket.sendall(file_data)
                print(f"file {filename} sended successfully")
                
        except FileNotFoundError:
            print(f"file {filename} not exist")
        except Exception as e:
            print(f"send error: {e}")
            
    def close(self):
        """关闭连接"""
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        print("连接已关闭")

    def start_TCP_client():
        import argparse
        
        parser = argparse.ArgumentParser(description='TCP client')
        parser.add_argument('--host', default='127.0.0.1', help='server address')
        parser.add_argument('--port', type=int, default=65432, help='server port')
        parser.add_argument('--file', help='send file')
        
        args = parser.parse_args()
        
        client = TCPClient_Base(host=args.host, port=args.port)
        
        if not client.connect():
            sys.exit(1)
            
        try:
            if args.file:
                client.file_transfer_mode(args.file)
                time.sleep(2)
            else:
                client.interactive_mode()
        except KeyboardInterrupt:
            print("\nclient shutting down...")
        finally:
            client.close()




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
        self.clients = {}  # 存储客户端信息
        self.running = False
        self.client_lock = threading.Lock()
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
            
            # del disconnected clients
            for addr in disconnected_clients:
                if addr in self.clients:
                    print(f"清理断开连接的客户端: {addr}")
                    self.clients[addr]['socket'].close()
                    del self.clients[addr]
    
    def handle_client(self, client_socket, client_address):
        """处理客户端连接"""
        client_id = f"{client_address[0]}:{client_address[1]}"
        
        with self.client_lock: # add new client
            self.clients[client_address] = {
                'socket': client_socket,
                'address': client_address,
                'id': client_id,
                'connected_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        print(f"新客户端连接: {client_id}")
        print(f"当前连接数: {len(self.clients)}")
        
        # 发送欢迎消息
        welcome_msg = f"欢迎连接到服务器！您的ID: {client_id}\n"
        client_socket.sendall(welcome_msg.encode('utf-8'))
        
        try:
            while True:
                # 接收数据
                data = client_socket.recv(4096)
                if not data:
                    break
                    
                # 解码消息
                message = data.decode('utf-8').strip()
                
                # 处理特殊命令
                if message.startswith('/'):
                    response = self.handle_command(client_socket, client_address, message)
                else:
                    # 普通消息处理
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_msg = f"[{timestamp}] {client_id}: {message}"
                    print(log_msg)
                    
                    # 广播消息给其他客户端
                    broadcast_msg = f"[{timestamp}] 客户端 {client_id}: {message}"
                    self.broadcast(broadcast_msg, exclude_client=client_address)
                    
                    response = f"消息已发送: {message}"
                    
                # 发送响应
                if response:
                    client_socket.sendall(response.encode('utf-8'))
                    
        except ConnectionResetError:
            print(f"客户端断开连接: {client_id}")
        except Exception as e:
            print(f"处理客户端 {client_id} 时出错: {e}")
        finally:
            with self.client_lock:
                if client_address in self.clients:
                    del self.clients[client_address]
            client_socket.close()
            print(f"客户端断开: {client_id}")
            print(f"当前连接数: {len(self.clients)}")
            
    def handle_command(self, client_socket, client_address, command):
        """处理特殊命令"""
        client_id = f"{client_address[0]}:{client_address[1]}"
        
        if command == '/help':
            help_text = """
            可用命令:
            /help - 显示帮助信息
            /time - 显示服务器时间
            /clients - 显示在线客户端
            /quit - 断开连接
            """
            return help_text
            
        elif command == '/time':
            return f"服务器时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
        elif command == '/clients':
            with self.client_lock:
                client_list = [info['id'] for info in self.clients.values()]
                return f"在线客户端 ({len(client_list)}): {', '.join(client_list)}"
                
        elif command == '/quit':
            return "再见！"
            
        else:
            return f"未知命令: {command}"
            
    def start(self):
        """启动服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_clients)
            
            self.running = True
            print(f"高级TCP服务器启动在 {self.host}:{self.port}")
            print(f"最大连接数: {self.max_clients}")
            print("输入 'stop' 停止服务器\n")
            
            # 启动控制台输入线程
            input_thread = threading.Thread(target=self.console_input, daemon=True)
            input_thread.start()
            
            # 主循环接收连接
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    
                    if len(self.clients) >= self.max_clients:
                        client_socket.sendall("服务器已达到最大连接数，请稍后再试。".encode('utf-8'))
                        client_socket.close()
                        continue
                    
                    # 为新客户端创建线程
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except OSError:
                    # 服务器套接字被关闭时退出循环
                    break
                    
        except Exception as e:
            print(f"服务器错误: {e}")
        finally:
            self.stop()
            
    def console_input(self):
        """处理控制台输入"""
        while self.running:
            try:
                cmd = input().strip().lower()
                if cmd == 'stop':
                    print("正在停止服务器...")
                    self.running = False
                    self.stop()
                elif cmd == 'status':
                    print(f"当前连接数: {len(self.clients)}")
                    print(f"服务器运行中: {self.running}")
                elif cmd == 'clients':
                    with self.client_lock:
                        for addr, info in self.clients.items():
                            print(f"  {info['id']} - 连接时间: {info['connected_time']}")
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
            print("服务器已停止")



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
            
            print(f"正在连接到 {self.host}:{self.port}...")
            self.client_socket.connect((self.host, self.port))
            
            self.running = True
            
            # 启动接收消息线程
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            print("连接成功！输入 '/help' 查看可用命令")
            return True
            
        except socket.timeout:
            print("连接超时")
            return False
        except ConnectionRefusedError:
            print("连接被拒绝，请确保服务器正在运行")
            return False
        except Exception as e:
            print(f"连接错误: {e}")
            return False
            
    def receive_messages(self):
        """接收服务器消息"""
        buffer = ""
        while self.running:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    print("\n连接已断开")
                    self.running = False
                    break
                    
                buffer += data.decode('utf-8')
                
                # 处理可能的分行消息
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        print(f"\n[服务器] {line}")
                        
            except socket.timeout:
                continue
            except ConnectionResetError:
                print("\n连接被重置")
                self.running = False
                break
            except Exception as e:
                print(f"\n接收消息错误: {e}")
                self.running = False
                break
                
    def send_message(self, message):
        """发送消息到服务器"""
        if not self.running or not self.client_socket:
            print("未连接到服务器")
            return False
            
        try:
            # 添加换行符以便服务器区分消息
            if not message.endswith('\n'):
                message += '\n'
                
            self.client_socket.sendall(message.encode('utf-8'))
            return True
            
        except Exception as e:
            print(f"发送消息错误: {e}")
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
                    print("\n正在断开连接...")
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
                print(f"文件 {filename} 已发送")
                
        except FileNotFoundError:
            print(f"文件 {filename} 不存在")
        except Exception as e:
            print(f"文件传输错误: {e}")
            
    def close(self):
        """关闭连接"""
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        print("连接已关闭")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='高级TCP客户端')
    parser.add_argument('--host', default='127.0.0.1', help='服务器地址')
    parser.add_argument('--port', type=int, default=65432, help='服务器端口')
    parser.add_argument('--file', help='发送文件')
    
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
        print("\n客户端正在关闭...")
    finally:
        client.close()


# if __name__ == "__main__":
#     server = TCPServer_Base(host='127.0.0.1', port=65432, max_clients=10)
#     server.start()

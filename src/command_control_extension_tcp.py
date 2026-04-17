# # command_protocol_extension.py
# """
# 扩展协议库：为 TCP_Server_Base / TCP_Client_Base 实例添加远程命令执行功能。
# 使用方法：
#     from connect_tcp import TCP_Server_Base, TCP_Client_Base
#     from command_protocol_extension import install_server_extensions, install_client_extensions

#     server = TCP_Server_Base(...)
#     install_server_extensions(server, log_file="my_commands.log")

#     client = TCP_Client_Base(...)
#     install_client_extensions(client)
# """

# # command_protocol_extension.py
# import os
# import sys
# import uuid
# import shlex
# import logging
# import subprocess
# import threading
# import time
# import ast
# from datetime import datetime

# def install_server_extensions(server_instance, log_file="command_execution.log"):
#     """为 TCP_Server_Base 实例安装扩展"""
#     # 初始化日志
#     server_instance._cmd_logger = _setup_logger(log_file)
#     server_instance._active_commands = {}
#     server_instance._active_commands_lock = threading.Lock()

#     # 注册命令处理器（使用闭包捕获 server_instance）
#     server_instance.register_command(
#         "/command",
#         lambda sock, addr, cmd: _server_handle_console_command(server_instance, sock, addr, cmd),
#         where_to_run="client",
#         run_in_thread=False
#     )
#     server_instance.register_command(
#         "/command_output",
#         lambda sock, addr, cmd: _server_handle_command_output(server_instance, sock, addr, cmd),
#         where_to_run="server",
#         run_in_thread=False
#     )
#     server_instance.register_command(
#         "/command_done",
#         lambda sock, addr, cmd: _server_handle_command_done(server_instance, sock, addr, cmd),
#         where_to_run="server",
#         run_in_thread=False
#     )
#     # 可选：打印注册成功信息
#     print(f"[Extension] Server extension installed. Available commands: {list(server_instance._custom_handlers[1].keys())}")


# def install_client_extensions(client_instance):
#     """为 TCP_Client_Base 实例安装扩展"""
#     client_instance.register_command(
#         "/run_command",
#         lambda sock, addr, cmd: _client_handle_run_command(client_instance, sock, addr, cmd),
#         where_to_run="server",
#         run_in_thread=False
#     )
#     print("[Extension] Client extension installed.")


# # ------------------ 服务端处理器 ------------------
# def _setup_logger(log_file):
#     logger = logging.getLogger(f"CmdExt_{id(log_file)}")
#     logger.setLevel(logging.INFO)
#     if not logger.handlers:
#         fh = logging.FileHandler(log_file, encoding="utf-8")
#         fh.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
#         logger.addHandler(fh)
#         logger.propagate = False
#     return logger

# def _parse_address(token):
#     """解析地址 token，支持 (127.0.0.1,65427) 或带引号的字符串"""
#     token = token.strip()
#     # 去除可能的外层引号
#     if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
#         token = token[1:-1]
#     try:
#         # 尝试用 ast.literal_eval 解析元组
#         addr = ast.literal_eval(token)
#         if isinstance(addr, tuple) and len(addr) == 2 and isinstance(addr[0], str) and isinstance(addr[1], int):
#             return addr
#     except:
#         pass
#     return None

# def _server_handle_console_command(server_inst, client_socket, client_address, command_line):
#     parts = shlex.split(command_line)
#     if not parts or parts[0].lower() != "/command":
#         return "Usage: /command <cmd1> <cmd2> ... <addr1> <addr2> ..."

#     parts = parts[1:]
#     if not parts:
#         return "Error: missing arguments."

#     # 解析命令-地址组
#     command_groups = []
#     current_cmds = []
#     current_addrs = []

#     def flush():
#         if current_cmds and current_addrs:
#             command_groups.append((current_cmds.copy(), current_addrs.copy()))
#             current_cmds.clear()
#             current_addrs.clear()

#     for token in parts:
#         addr = _parse_address(token)
#         if addr:
#             flush()  # 新地址组开始前，保存之前的命令组
#             current_addrs.append(addr)
#         else:
#             current_cmds.append(token)
#     flush()

#     if not command_groups:
#         return "Error: no valid command-address groups found. Use format: /command cmd1 cmd2 (ip,port) (ip,port) cmd3 ..."

#     total_sent = 0
#     for cmds, addrs in command_groups:
#         for cmd in cmds:
#             for addr in addrs:
#                 if addr not in server_inst.clients:
#                     server_inst._cmd_logger.warning(f"Client {addr} not connected, cannot send command: {cmd}")
#                     continue
#                 cmd_id = uuid.uuid4().hex
#                 with server_inst._active_commands_lock:
#                     server_inst._active_commands[cmd_id] = {
#                         "client_addr": addr,
#                         "command": cmd,
#                         "start_time": time.time()
#                     }
#                 client_sock = server_inst.clients[addr]["socket"]
#                 server_inst.send_message(client_sock, f"/run_command {cmd_id} {cmd}\n")
#                 total_sent += 1
#                 server_inst._cmd_logger.info(f"Sent command [{cmd_id}] to {addr}: {cmd}")
#     return f"Sent {total_sent} command(s) to client(s)."


# def _server_handle_command_output(server_inst, client_socket, client_address, message):
#     parts = message.split(maxsplit=2)
#     if len(parts) < 3:
#         return
#     _, cmd_id, output_line = parts
#     with server_inst._active_commands_lock:
#         cmd_info = server_inst._active_commands.get(cmd_id)
#     if cmd_info:
#         client_addr = cmd_info["client_addr"]
#         log_msg = f"[CMD:{cmd_id}] [{client_addr[0]}:{client_addr[1]}] {output_line}"
#     else:
#         log_msg = f"[CMD:{cmd_id}] [unknown client] {output_line}"
#     server_inst._cmd_logger.info(log_msg)


# def _server_handle_command_done(server_inst, client_socket, client_address, message):
#     parts = message.split()
#     if len(parts) < 3:
#         return
#     _, cmd_id, exit_code_str = parts
#     try:
#         exit_code = int(exit_code_str)
#     except:
#         exit_code = -1

#     with server_inst._active_commands_lock:
#         cmd_info = server_inst._active_commands.pop(cmd_id, None)

#     if cmd_info:
#         client_addr = cmd_info["client_addr"]
#         command = cmd_info["command"]
#         elapsed = time.time() - cmd_info["start_time"]
#         result = "success" if exit_code == 0 else "fail"
#         print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
#               f"{client_addr[0]}:{client_addr[1]} "
#               f"\"{command}\" {result} (exit={exit_code}, {elapsed:.2f}s)")
#         server_inst._cmd_logger.info(f"[CMD:{cmd_id}] FINISHED exit={exit_code} result={result}")
#     else:
#         server_inst._cmd_logger.warning(f"Received command_done for unknown cmd_id: {cmd_id}")


# # ------------------ 客户端处理器 ------------------
# def _client_handle_run_command(client_inst, client_socket, client_address, message):
#     parts = message.split(maxsplit=2)
#     if len(parts) < 3:
#         client_inst.send_message(client_socket, "/command_done unknown -1\n")
#         return
#     _, cmd_id, command = parts

#     def execute():
#         try:
#             proc = subprocess.Popen(
#                 command,
#                 shell=True,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.STDOUT,
#                 text=True,
#                 bufsize=1,
#                 encoding=sys.getfilesystemencoding()
#             )
#             for line in iter(proc.stdout.readline, ''):
#                 if not line:
#                     break
#                 line = line.rstrip('\n')
#                 if line:
#                     client_inst.send_message(client_socket, f"/command_output {cmd_id} {line}\n")
#             return_code = proc.wait()
#             client_inst.send_message(client_socket, f"/command_done {cmd_id} {return_code}\n")
#         except Exception as e:
#             client_inst.send_message(client_socket, f"/command_output {cmd_id} Error: {str(e)}\n")
#             client_inst.send_message(client_socket, f"/command_done {cmd_id} -1\n")

#     threading.Thread(target=execute, daemon=True).start()


# # ------------------- 使用示例 -------------------
# # if __name__ == "__main__":
# #     # 该部分仅用于演示，实际使用时应将本模块作为库导入
# #     from connect_tcp import TCP_Server_Base, TCP_Client_Base
# #     import sys

# #     if len(sys.argv) > 1 and sys.argv[1] == "server":
# #         server = TCP_Server_Base(host='127.0.0.1', port=65432, max_clients=10, is_input_command_in_console=True)
# #         install_server_extensions(server, log_file="server_commands.log")
# #         # 服务端会进入主循环，控制台输入 /command ... 即可使用
# #     elif len(sys.argv) > 1 and sys.argv[1] == "client":
# #         client = TCP_Client_Base(host='127.0.0.1', port=65432, client_host='127.0.0.1', is_input_command_in_console=True, is_wait_server=True)
# #         install_client_extensions(client)
# #         # 客户端启动后自动连接服务器，并等待服务端发送命令
# #     else:
# #         print("Usage: python command_protocol_extension.py [server|client]")


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

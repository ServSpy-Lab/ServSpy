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
from . import connect_tcp
        client_id = f"{client_address[0]}:{client_address[1]}"
        with self.client_lock:
            self.clients[client_address] = {
                'socket': client_socket,
                'address': client_address,
                'id': client_id,
                'connected_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        print(f"new connection: {client_id}")
        print(f"connection count mount: {len(self.clients)}")
        welcome_msg = f"Welcome!: {client_id}\n"
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
                data = self.recieve_message(client_socket, 4096)
                print(data)
                if not data:
                    break
                buffer+=data.decode("utf-8")
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    message = line.strip()
                    if not message:
                        continue
                    print(message)
                    if message.startswith('/'):
                        response = self.handle_command(
                            client_socket, client_address, message)
                    else:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        log_msg = f"[{timestamp}] {client_id}: {message}"
                        print(log_msg)
                        response = f"msg send: {message}"
                    if response:
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
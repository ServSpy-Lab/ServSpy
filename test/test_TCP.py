import os
import sys
import time
import multiprocessing
package_dictionary=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if package_dictionary not in os.sys.path:
    sys.path.insert(0, package_dictionary)
from src import connect_tcp
class TestConnect:
    def __init__(self):
        client_processes=[]
        setup_client_times=int(input())
        TCP_server_process=multiprocessing.Process(target=connect_tcp.TCPServer_Base)
        TCP_server_process.daemon=False
        TCP_server_process.start()
        time.sleep(2)
        for i in range(setup_client_times):
            TCP_client_process=multiprocessing.Process(target=connect_tcp.TCPClient_Base)
            TCP_client_process.daemon=False
            TCP_client_process.start()
            time.sleep(0.5)
        try:
            TCP_server_process.join()
            for client in client_processes:
                if client.is_alive():
                    client.terminate()
                    client.join()
        except KeyboardInterrupt:
            print("\n程序被用户中断")
            for client in client_processes:
                if client.is_alive():
                    client.terminate()
            TCP_server_process.terminate()
    # def test_TCP_server(self):
    #     pass
if __name__=="__main__":
    TestConnect()









import os
import sys
import time
import subprocess
package_dictionary=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if package_dictionary not in os.sys.path:
    sys.path.insert(0, package_dictionary)
class TestConnect:
    def __init__(self):
        create_tcp_client_amount=int(input())
        self.TCP_server_process=subprocess.Popen(
            ["python", os.path.join(os.path.dirname(__file__), 'test_TCP_server.py')], 
            creationflags=subprocess.CREATE_NEW_CONSOLE)
        time.sleep(2)
        for i in range(create_tcp_client_amount):
            time.sleep(0.5)
            subprocess.Popen(
                ["python", os.path.join(os.path.dirname(__file__), 'test_TCP_client.py')], 
                creationflags=subprocess.CREATE_NEW_CONSOLE)
if __name__=="__main__":
    TestConnect()

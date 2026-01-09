import os
import sys
package_dictionary=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if package_dictionary not in os.sys.path:
    sys.path.insert(0, package_dictionary)
from src import connect_tcp
def test_TCP_server():
    connect_tcp.TCPServer_Base()
test_TCP_server()

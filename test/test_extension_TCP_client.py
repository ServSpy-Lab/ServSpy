import os
import sys
package_dictionary=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# package_dictionary=os.path.dirname(os.path.abspath(__file__))
if package_dictionary not in os.sys.path:
    sys.path.insert(0, package_dictionary)
from src.connect_tcp import TCP_Client_Base
from src.command_control_extension_tcp import client_setup

client_setup()

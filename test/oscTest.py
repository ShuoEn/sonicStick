import OSC
import time

partner = OSC.OSCClient()
partner.connect(('127.0.0.1', 8000))   # localhost, port 57120
oscmsg = OSC.OSCMessage()
oscmsg.setAddress("/status")
current_pos='string Test'
oscmsg.append(current_pos)
partner.send(oscmsg)
time.sleep(5)
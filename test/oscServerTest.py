import OSC
import time
import _thread,threading
def OSC_init():
    OSCrec = OSC.OSCServer( ("0.0.0.0", 8000) )
    OSCrec.timeout = 0.05
    OSCrec.addMsgHandler( "/status", user_callback )
    _thread.start_new_thread(OSCrec.serve_forever,())

def user_callback(path, tags, args, source):
    print(args[0])

OSC_init()

while True:
	time.sleep(0.1)
	pass

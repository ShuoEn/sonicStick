import socket,time
import traceback
HOST = '192.168.1.4'
PORT = 8999
#s.connect((HOST, PORT))
while True:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        #cmd = raw_input("Please input msg:")
        print('recv:')
        #s.send(cmd)
        data = s.recv(1024)
        print data
        if(data=='home'):
            s.send('OK')
            print('Go home')
            s.close()
            break
    except:
        #traceback.print_exc()
        print('partner still sleep')
    time.sleep(0.5)
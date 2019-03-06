import socket

HOST = '192.168.1.4'
PORT = 8999

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(5)

print 'Server start at: %s:%s' %(HOST, PORT)
print 'wait for connection...'

while True:
    try:
        conn, addr = s.accept()
        print 'Connected by ', addr
        print('sent cmd home')
        conn.send("home")
        data = conn.recv(1024)
        print('data len='+str(len(data))+'data='+data)
        if(data=='OK'):
            print('Go home')
            conn.close()
            break
    except:
        print('disconnected')
print('bye')
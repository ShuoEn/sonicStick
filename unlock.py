import fcntl

lockfile = '/home/pi/sonicStick/fcntl.lock'
try:
    f = open(lockfile, 'r')
except IOError:
    f = open(lockfile, 'wb')
fcntl.flock(f, fcntl.LOCK_UN)
print('Unlock file')
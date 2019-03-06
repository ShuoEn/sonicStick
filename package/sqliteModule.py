#!/usr/bin/python

import sqlite3
import traceback
import os
#from IPython import embed
class PositionStorage():
    def __init__(self):
        # initial for DB
        self.conn = sqlite3.connect('motorPos.db')
        print "Opened database successfully"
        self.c = self.conn.cursor()
        try:
            self.c.execute('''CREATE TABLE POSITION
                (ID INT PRIMARY KEY     NOT NULL,
                POS           INT    NOT NULL);''')
            print "Table created successfully"
            self.conn.commit()


            self.c.execute("INSERT INTO POSITION (ID,POS) \
                VALUES (1, -1 )")

            self.conn.commit()
        except Exception,err:
            traceback.print_exc()
    def __del__(self):
        self.conn.close()
    def update_position(self,pos):
        self.c.execute("UPDATE POSITION set POS = "+str(pos)+" where ID=1")
        self.conn.commit()
        print('Updated pos:'+str(pos))
        #print "Total number of rows updated :", self.conn.total_changes
    def read_last_pos(self):
        try:
            self.cursor = self.c.execute("SELECT id, pos from POSITION")
            for row in self.cursor:
                return row[1]
        except Exception,err:
            traceback.print_exc()
            return None
    def print_data(self):
        self.cursor = self.c.execute("SELECT id, pos from POSITION")
        for row in self.cursor:
            print "ID = ", row[0]
            print "POS = ", row[1], "\n"

def checkHostAlive(hostname):
    response = os.system("ping -c 1 -w3 " + hostname )
    if(response==0):
        print(hostname,' alive')
        return True
    else:
        print(hostname,' dead')
        return False

def int32(x):
  if x>0xFFFFFFFF:
    raise OverflowError
  if x>0x7FFFFFFF:
    x=int(0x100000000-x)
    if x<2147483648:
      return -x
    else:
      return -2147483648
  return x
def ConvertFloat16ToRegister(floatValue):
    #ba = bytearray(struct.pack("f", floatValue))  
    # a=numpy.float16(floatValue)
    # b=a.tobytes()
    myList = list()
    s = bytearray(struct.pack('<f', floatValue))       #little endian
    myList.append(s[0] | (s[1]<<8))         #Append Least Significant Word  
    myList.append(s[2] | (s[3]<<8))         #Append Most Significant Word      

    return myList
# cheatsheet
'''
self.modbusClient.WriteSingleRegister(0x030C, 0xE0, 1)                      # Enable manual DI setting
self.modbusClient.WriteSingleRegister(0x040E, 0xE1, 1)                      # Manual touch endstop
self.modbusClient.WriteSingleRegister(0x030C, 0x00, 1)                      # Enable manual DI setting
holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0520, 2,1)      # Read current position
self.modbusClient.WriteMultipleRegisters(0x0510, [val & 0xFFFF, val >> 16],1) # Max positive PUU

'''
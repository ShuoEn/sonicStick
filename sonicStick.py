#!/usr/bin/python
from package.modbus.ModbusClient import *
import time
import OSC
import _thread,threading
import sys, traceback
import types
import math
import random
import argparse
import commands
from package.sqliteModule import *
import ctypes

#from IPython import embed
class SonicStick():
    def __init__(self):
        self.safe=False
        self.queue_mutex=threading.Lock()
        self.prQueue=PrQueue()
        self.ID_init()
        self.nowwho=1
        self.partnerPos=None
        self.lastpos=None
        self.DbObj=PositionStorage()
        self.modbus_init()
        self.artnet_init()
        self.OSC_init()
        
        # functions queue
        
    def __del__(self):
        try:
            self.modbusClient.close()
            self.sock.close()
            self.server.close()
        except:
            pass
    def modbus_init(self): 
        self.modbusClient = ModbusClient('/dev/serial0') #COM37') #modbusClient = ModbusClient('127.0.0.1', 502)
        #self.modbusClient.Parity = Parity.odd
        self.modbusClient.Parity = Parity.even
        self.modbusClient.UnitIdentifier = 1
        self.modbusClient.Baudrate = 115200
        self.modbusClient.Stopbits = Stopbits.one
        #self.modbusClient.timeout = 0.001
        self.modbusClient.Connect()
        self.deviceAddr = 1
    def artnet_init(self):
        self.func_list = []
        howmanylevel = 256
        self.posdmx = [0] * howmanylevel
        self.spddmx = [0] * howmanylevel
        self.accdmx = [0] * howmanylevel
        #dividee = (60000000/howmanylevel)
        dividee = (60000000/howmanylevel)
        speedee = (6500/howmanylevel)
        accee = (18000/howmanylevel)
        for ii in range(0,howmanylevel):
            self.posdmx[howmanylevel-ii-1] = int(ii * dividee)
            self.spddmx[ii] = int(ii * speedee) + 2500
            self.accdmx[ii] = 21000 - int(ii * accee )
        for ii in range(0,howmanylevel):
            #print (self.posdmx[ii])
            pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        #self.sock.settimeout(3)
        self.sock.bind(("0.0.0.0", 6454))
        
    def ID_init(self):
        ips = commands.getoutput("/sbin/ifconfig | grep -iA2 \"eth0\" | grep -i \"inet\" | grep -iv \"inet6\" | " +
                         "awk {'print $2'} ") # | sed -ne 's/addr\://p'")
        iplist = ips.split(".")
        self.IP = ips
        self.ID = int(iplist[3]) 
        print('ID='+str(self.ID)+' IP='+self.IP)
        self.server='192.168.1.201'
        self.partner='192.168.1.'
        if (self.ID)%2==0:
            self.partner=self.partner+str(self.ID-1)
        else:
            self.partner=self.partner+str(self.ID+1)
    def get_partner_ip(self):
        # get from server first or using local lookup table
        pass
    def OSC_init(self):
        self.server = OSC.OSCServer( ("0.0.0.0", 7730) )
        self.server.timeout = 0.05
        self.server.addMsgHandler( "/motor", self.user_callback )
        self.server.addMsgHandler( "/stop", self.stop_callback )
        self.server.addMsgHandler( "/lastpos", self.pos_sync_callback )
        _thread.start_new_thread(self.server.serve_forever,())
    # def socket_to_partner(self):
    #     self.socket_partner = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     if(self.ID%2==0): # slave
    #         pass

    def pos_sync_callback(self, path, tags, args, source):
        self.partnerPos=args[0]

    #thread mutex? have done in ModbusClient module
    def send_pos(self):
        partner = OSC.OSCClient()
        partner.connect((self.partner, 7730))   # localhost, port 57120
        oscmsg = OSC.OSCMessage()
        oscmsg.setAddress("/lastpos")
        while True:
            current_pos=self.read_current_pos()
            oscmsg.append(current_pos)
            partner.send(oscmsg)
            time.sleep(5)
    #thread mutex? have done in ModbusClient module
    def save_pos_to_db(self):
        DbObj=PositionStorage()
        while True:
            current_pos=self.read_current_pos()
            DbObj.update_position(current_pos)
            time.sleep(0.7)
    def save_pos_to_db_once(self):
        current_pos=self.read_current_pos()
        self.DbObj.update_position(current_pos)
    def send_data_to_partner(self,node,data):
        partner = OSC.OSCClient()
        partner.connect((self.partner, 7730))   # localhost, port 57120
        oscmsg = OSC.OSCMessage()
        oscmsg.setAddress("/"+node)
        oscmsg.append(data)
        partner.send(oscmsg)
    def send_data_to_server(self,node,data):
        partner = OSC.OSCClient()
        partner.connect((self.server, 7730))   # localhost, port 57120
        oscmsg = OSC.OSCMessage()
        oscmsg.setAddress("/"+node)
        oscmsg.append(data)
        partner.send(oscmsg)
    def readInput(self):
        holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0204, 1) #holdingRegisters = ConvertRegistersToFloat(self.modbusClient.ReadHoldingRegisters(2304, 1))
        try:
            if(len(holdingRegisters)):
                if(833 == holdingRegisters[0]):
                    holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0024, 2, holdingRegisters[1]) #holdingRegisters = ConvertRegistersToFloat(self.modbusClient.ReadHoldingRegisters(2304, 1))
                    pos = self.posdmx[0] - (holdingRegisters[1] << 16) + holdingRegisters[0]
                    print pos
                    click( holdingRegisters[2], math.ceil( float(pos) / self.posdmx[0] * 127 ) )
            else:
                #pass
                print (unit)
        except IndexError, e:
            pass

    # Read position of last time ,then set software endstop
    def home(self):
        if(self.safe==False):
            print('not to home')
            return
        sync=self.partnerHomeSync()
        if not sync:
            print('home SYNC failure, not to home')
            return
        print('home')
        self.modbusClient.WriteSingleRegister(0x050E, 0,1) # Pr0 home
        time.sleep(0.025)
        #self.modbusClient.readmore(32)
        while True:
            holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0002, 2,1) # read alarm
            alarm=ConvertRegistersToDouble(holdingRegisters)
            holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x005C, 2,1) # read home state
            motorState=ConvertRegistersToDouble(holdingRegisters)
            homeState= (motorState & 256) == 256
            if alarm==0x285 or alarm==0x283:
                print('touch soft endstop')
                self.modbusClient.WriteSingleRegister(0x030C, 0xE0, 1) # Enable manual DI setting
                self.modbusClient.WriteSingleRegister(0x040E, 0xE1, 1) # Manual touch endstop
                self.modbusClient.WriteSingleRegister(0x030C, 0x00, 1) # Enable manual DI setting
                self.set_max_PUU(2147483647,-2147483648)
                return
            if homeState:
                print('home safety')
                #self.set_max_PUU(2147483647,-2147483648)
                return
            time.sleep(0.1)
    def partnerHomeSync(self):
        print('waiting for home sync')
        PORT=8999
        # Setting as slave or master
        if(self.ID%2!=0): #slave
            while True:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((self.partner, PORT))
                    print('recv:')
                    data = s.recv(1024)
                    print data
                    if(data=='home'):
                        s.send('OK')
                        print('Go home')
                        s.close()
                        return True
                except (KeyboardInterrupt, SystemExit):

                    raise
                except:
                    #traceback.print_exc()
                    print('partner still sleep')
                time.sleep(0.5)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((self.IP, PORT)) #socket.gethostname() '192.168.11.4'
            s.listen(5)
            while True:
                try:
                    conn, addr = s.accept()
                    print 'Connected by ', addr
                    # if addr == self.partner:
                    print('sent cmd home')
                    conn.send("home")
                    data = conn.recv(1024)
                    print('data len='+str(len(data))+'data='+data)
                    if(data=='OK'):
                        print('Go home')
                        conn.close()
                        return True
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    #print('disconnected')
                    traceback.print_exc()
        return False
    # ---check list---
    # remote server
    # partner
    #  
    def safetyCheck(self):
        self.lastpos=self.DbObj.read_last_pos()

        if self.lastpos==None:
            self.safe=False
            print('safety checking failure, couldn\'t read last position')
            return False
        else:
            print('Read from DB, last position:'+str(self.lastpos)) 
            self.set_max_PUU(2147483647,-self.lastpos) # Max PUU
        # check server and partner
        while False:#True: remember to fix back
            partnerRUOK=checkHostAlive(self.partner)
            if(checkHostAlive(server) and partnerRUOK):
                self.safe=True
                return False
            else:
                print('safe checking failure, STOP motor')
                self.modbusClient.WriteSingleRegister(0x050E, 1000, 1) # Stop motor
                break
            time.sleep(5)
        while False: # check modbus responses
            if(self.read_current_pos()==None):
                print('safety check failure: No modbus responses')
            else:
                break
        print('safety pass')
        self.safe=True
        return True
    def stop_callback(self, path, tags, args, source):
        print "stop", args[0]
        self.modbusClient.WriteSingleRegister(0x050E, 1000, 1)
        
    # def moveMotor(self, howmany, speed, acc):
    #     print('move')
    #     motordistance = self.posdmx[howmany] #1000000
    #     speed=int(round(speed/16.0))
    #     acc=int(round(acc/16.0))
    #     # setting_val=0x00000023 | (acc<<8) |(acc<<12)|(speed<<16)
    #     # self.modbusClient.WriteMultipleRegisters(self.prQueue.nextPrSettingAddr, [motordistance & 0xFFFF, motordistance >> 16],1)
    #     # time.sleep(0.025)
    #     print('addr='+str(self.prQueue.nextPrPathAddr)+' x='+str(motordistance))
    #     self.modbusClient.WriteMultipleRegisters(self.prQueue.nextPrPathAddr, [motordistance & 0xFFFF, motordistance >> 16],1)
    #     time.sleep(0.025)
    def moveMotor(self, howmany, speed, acc,Praddr):
        print('move')
        motordistance = self.posdmx[howmany] #1000000
        speed=int(round(speed/16.0))
        acc=int(round(acc/16.0))
        # setting_val=0x00000023 | (acc<<8) |(acc<<12)|(speed<<16)
        # self.modbusClient.WriteMultipleRegisters(self.prQueue.nextPrSettingAddr, [motordistance & 0xFFFF, motordistance >> 16],1)
        # time.sleep(0.025)
        print('Pr_Addr='+str(hex(Praddr))+' x='+str(motordistance))
        self.modbusClient.WriteMultipleRegisters(Praddr, [motordistance & 0xFFFF, motordistance >> 16],1)
        time.sleep(0.025)
    def set_acc(self,row,acc):
        print('set speed')
        if(row>15 or row <0 or acc==0):
            return
        if(acc>65500):
            acc=65500
        addr=0x0528+row*4
        self.modbusClient.WriteMultipleRegisters(addr, [acc & 0xFFFF, acc >> 16],1)
        time.sleep(0.025)
    def set_speed(self,row,speed):
        print('set speed')
        if(row>15 or row <0 or speed==0):
            return
        if(speed>65500):
            speed=65500
        addr=0x0578+row*4
        self.modbusClient.WriteMultipleRegisters(addr, [speed & 0xFFFF, speed >> 16],1)
        time.sleep(0.025)
    def set_max_PUU(self,positivePUU,negtivePUU):
        negtivePUU=int32(negtivePUU)
        positivePUU=int32(positivePUU)
        self.modbusClient.WriteMultipleRegisters(0x0510, [positivePUU & 0xFFFF, positivePUU >> 16],1)
        self.modbusClient.WriteMultipleRegisters(0x0512, [negtivePUU & 0xFFFF, negtivePUU >> 16],1)
    def JogMotor(self, unit, JogWhat):
        
        self.modbusClient.UnitIdentifier = unit
        holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0900, 1) #holdingRegisters = ConvertRegistersToFloat(self.modbusClient.ReadHoldingRegisters(2304, 1))
        print (holdingRegisters)

        if holdingRegisters[0] == 0x0ff0:
            #self.modbusClient.WriteSingleRegister(0x0901, 0, unit)
            
            self.modbusClient.WriteSingleRegister(0x0901, 3, unit)
            self.modbusClient.WriteSingleRegister(0x0902, 1000, unit)
            self.modbusClient.WriteSingleRegister(0x0903, 20, unit)
            #print ("{:04x}".format(abs(howmany) >> 16))
            self.modbusClient.WriteSingleRegister(0x0904, JogWhat, unit)
            holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0024, 2) #holdingRegisters = ConvertRegistersToFloat(self.modbusClient.ReadHoldingRegisters(2304, 1))
            #print (holdingRegisters)
            
        else:
            print ("something wrong")

    def artnet_handler(self, socket,fortuple):
        print('artnet_handler')
        lastpos = 0
        lastspeed = 0
        lastacc = 0
        while True:
            if(self.safe ==False):
                time.sleep(0.01)
                continue
            try:
                #print('-a')
                data, addr = socket.recvfrom(1024)
                #print('-b')
                if ((len(data) > 18) and (data[0:8] == "Art-Net\x00")):
                    rawbytes = map(ord, data)
                    opcode = rawbytes[8] + (rawbytes[9] << 8)
                    protocolVersion = (rawbytes[10] << 8) + rawbytes[11]
                    if ((opcode == 0x5000) and (protocolVersion >= 14)):
                        sequence = rawbytes[12]
                        physical = rawbytes[13]
                        sub_net = (rawbytes[14] & 0xF0) >> 4
                        universe = rawbytes[14] & 0x0F
                        net = rawbytes[15]
                        rgb_length = (rawbytes[16] << 8) + rawbytes[17]
                        #print "seq %d phy %d sub_net %d uni %d net %d len %d" % \
                        #(sequence, physical, sub_net, universe, net, rgb_length)
                        idx = 18
                        if universe == 0 and ( rawbytes[idx+self.ID] != lastspeed or rawbytes[idx+self.ID-1] != lastpos or rawbytes[idx+self.ID+1] != lastacc ):
                            #print ("1 %d 5 %d 7 %d 13 %d" % (lastpos , lastspeed, rawbytes[idx+9], rawbytes[idx+10]))
                            lastpos = rawbytes[idx+self.ID-1]
                            lastspeed = rawbytes[idx+self.ID]
                            lastacc = rawbytes[idx+self.ID+1]
                            print('func append')
                            self.prQueue.append(lastpos, lastspeed, lastacc )
                            #self.prQueue.append(lambda : self.moveMotor(lastpos, lastspeed, lastacc,self.prQueue.nextPrPathAddr ))
                            # if len(self.func_list) > 0:
                                # self.func_list[0] =  ( lambda : self.moveMotor(lastpos, lastspeed, lastacc ) )
                            # else:
                                # self.func_list.append( lambda : self.moveMotor(lastpos, lastspeed, lastacc ) )
            except Exception, err: 
                print "*** print_exc:"
                traceback.print_exc()
        
    def user_callback(self, path, tags, args, source):
        print('user call')
        # which user will be determined by path:
        # we just throw away all slashes and join together what's left
        # user = ''.join(path.split("/"))
        # tags will contain 'fff'
        # args is a OSCMessage with data
        # source is where the message came from (in case you need to reply)
        if args[0] == 1:
            print "\n"
            print (args[0], args[1], args[2], args[3]) 
        #global self.func_list
        #self.func_list.append( lambda : moveMotor( args[0], args[1], args[2], args[3] ) )
        #self.moveMotor( args[0], args[1], args[2], args[3] ) 
    
    # Pop motor command and run
    def motor_command_routine(self):
        while True:
            #print('hello')
            time.sleep(0.01)
            #if(self.prQueue.queueLock is False):
            
            if(len(self.prQueue.move_list)>=6):
                holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x050E,1,1)
                
                first_moveData=self.prQueue.move_list[0]
                last_moveData=self.prQueue.move_list[5]
                if(holdingRegisters[0]==
                for i in range(6):
                    self.queue_mutex.acquire()
                    moveData=self.prQueue.move_list.pop(0)
                    self.queue_mutex.release()
                    # PrPos, PrSpeed, PrAcc,self.nextPrPathAddr,self.nextPrNum
                    self.moveMotor(moveData[0],moveData[1],moveData[2],moveData[3])
                if(first_moveData[4]-1==0):
                    prNum=60
                else
                    prNum=first_moveData[4]-1
                self.connectPr(prNum)
                self.cutPr(last_moveData[4])
                
                
                    #time.sleep(0.01)
            # for func in self.prQueue.move_list:
            #     func()
            #     self.prQueue.move_list.pop(0)
            #     #time.sleep(0.25)
            # #time.sleep(0.001)
    def test(self):
        print('test')
        holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0520, 2,1)
        doubeVal=ConvertRegistersToDouble(holdingRegisters)
        print('pos=',ctypes.c_long(doubeVal).value)
        holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0002, 2,1)
        print('alarm=',ConvertRegistersToDouble(holdingRegisters))
        #val=0x00000023
        #self.modbusClient.WriteMultipleRegisters(0x0702, [val & 0xFFFF, val >> 16],1)
        # _thread.start_new_thread(self.get_Pr_data,())
        # self.modbusClient.WriteSingleRegister(0x050E, 1, 1)
        # time.sleep(0.25)
        # self.modbusClient.WriteSingleRegister(0x050E, 2, 1)
        # time.sleep(0.25)
        # self.modbusClient.WriteSingleRegister(0x050E, 3, 1)
        # time.sleep(0.25)
        # self.modbusClient.WriteSingleRegister(0x050E, 1, 1)
        # time.sleep(0.25)
    def read_current_pos(self):
        try:
            holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0520, 2,1)
            doubeVal=ConvertRegistersToDouble(holdingRegisters)
            return ctypes.c_long(doubeVal).value
        except Exception,err:
            print('read_current_pos err:')
            traceback.print_exc()
            return None
    def get_Pr_data(self):
        while True:
            holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x050E,1,1)
            print('Pr='+str(holdingRegisters))
            time.sleep(0.5)
    def run_Pr1(self):
        self.modbusClient.WriteSingleRegister(0x050E, 1, 1)
    def settings(self): # Pr
        print('Prs configuration')
        val=0x00000023
        start_addr=0x0604
        for i in range(49):
            self.modbusClient.WriteMultipleRegisters(start_addr, [val & 0xFFFF, val >> 16],1) # Define Pr1~Pr49
            self.modbusClient.WriteMultipleRegisters(start_addr+2, [0,0],1) # Path
            start_addr=start_addr+4
        start_addr=0x0700
        for i in range(12):
            self.modbusClient.WriteMultipleRegisters(start_addr, [val & 0xFFFF, val >> 16],1) # Define Pr50~Pr61
            self.modbusClient.WriteMultipleRegisters(start_addr+2, [0,0],1) # Path
            start_addr=start_addr+4
    def connectPr(self,num):
        self.modbusClient.WriteMultipleRegisters(start_addr, [val & 0xFFFF, val >> 16],1)
    def cutPr(self,num):
        self.modbusClient.WriteMultipleRegisters(start_addr, [val & 0xFFFF, val >> 16],1)
    def start(self): 
        _thread.start_new_thread(self.motor_command_routine,())
        _thread.start_new_thread(self.artnet_handler,(self.sock,0))
        _thread.start_new_thread(self.send_pos,())
        _thread.start_new_thread(self.save_pos_to_db,())
        self.run_Pr1()
        try:
            while True:
                time.sleep(0.1)
                pass
        except (KeyboardInterrupt, SystemExit):
            print('stop it')
            self.modbusClient.WriteSingleRegister(0x050E, 1000, 1)
class PrQueue():
    def __init__(self):
        #self.queueLock=False
        self.queue_mutex = threading.Lock()
        self.move_list=[]
        self.PrNum_list=[]
        self.currentPrNum=0 
        self.nextPrNum=1
        self.nextPrPathAddr=0x0606
        self.nextPrSettingAddr=0x0604
    def append(self,PrPos, PrSpeed, PrAcc):
        #self.queueLock=True
        self.queue_mutex.acquire()
        self.move_list.append( [PrPos, PrSpeed, PrAcc,self.nextPrPathAddr,self.nextPrNum] )
        self.queue_mutex.release()
        #self.PrNum_list.append( self.nextPrNum )
        print('append num='+str(self.nextPrNum))
        self.currentPrNum=self.currentPrNum+1
        self.nextPrNum=self.nextPrNum+1
        if self.nextPrNum==61:
            self.nextPrNum=1
        if(49>self.nextPrNum>0):
            self.nextPrPathAddr = 0x0606+(self.nextPrNum-1)*4
            self.nextPrSettingAddr=self.nextPrPathAddr-2
        else:
            self.nextPrPathAddr = 0x0702+(self.nextPrNum-49)*4
            self.nextPrSettingAddr=self.nextPrPathAddr-2       
        #self.queueLock=False
    # def getPrPathAddr(self,nextPrNum):
    #     if(59>nextPrNum>0):
    #         return 0x0606+(nextPrNum-1)*4
    #     else:
    #         return 0x0702+(nextPrNum-59)*4
if __name__ == '__main__':
    # Takes argument
    parser = argparse.ArgumentParser()
    parser.add_argument("--T", default="R")
    args = parser.parse_args()
    bigStick=SonicStick()
    if args.T=='W': # Write current position to DB
        bigStick.save_pos_to_db_once()
        bigStick.DbObj.print_data()
    elif args.T=='T': # test
        bigStick.safetyCheck()
        bigStick.settings()
        bigStick.home()
        bigStick.start() # Running forever 
        #bigStick.test()
        #embed()
    else:
        # will be in start
        #bigStick.settings()
        #bigStick.start() # Running forever
        pass


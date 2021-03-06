#!/usr/bin/python
# -*- coding: utf-8 -*-

from package.modbus.ModbusClient import *
import os
import time,datetime
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
import fcntl
from IPython import embed
class SonicStick():
    def __init__(self):
        self.safe=False
        #self.queue_mutex=threading.Lock()
        self.prQueue=PrQueue()
        self.ID_init()
        self.nowwho=1
        self.partnerPos=None
        self.lastpos=None
        self.DbObj=PositionStorage()
        self.modbus_init()
        self.artnet_init()
        self.OSC_init()
        # ex_alarm: modbus no response, tilted、partner alarm、partner dead
        self.status={'mode':'controled','alarm':0,'ex_alarm':0,'position':-999,'home':'homed'}

        # functions queue
        
    def __del__(self):
        try:
            self.modbusClient.close()
            self.sock.close()
            self.OSCrec.close()
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
            #self.posdmx[howmanylevel-ii-1] = int(ii * dividee)
            self.posdmx[ii] = int(ii * dividee)
            self.spddmx[ii] = int(ii * speedee) + 2500
            self.accdmx[ii] = int(ii * accee )
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
        self.OSCrec = OSC.OSCServer( ("0.0.0.0", 7730) )
        self.OSCrec.timeout = 0.05
        self.OSCrec.addMsgHandler( "/motor", self.user_callback )
        self.OSCrec.addMsgHandler( "/stop", self.stop_callback )
        self.OSCrec.addMsgHandler( "/lastpos", self.pos_sync_callback )
        self.OSCrec.addMsgHandler( "/mode", self.mode_callback ) # 
        _thread.start_new_thread(self.OSCrec.serve_forever,())

    def mode_callback(self, path, tags, args, source):
        if args[0]=='autorun':
            self.status['mode']=args[0]

        elif args[0]=='controled': # stop, clear buffer
            self.status['mode']=args[0]
            stop_callback()
        else:


    # def socket_to_partner(self):
    #     self.socket_partner = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     if(self.ID%2==0): # slave
    #         pass

    def pos_sync_callback(self, path, tags, args, source):
        self.partnerPos=args[0]

    def stop_callback(self, path, tags, args, source):
        #print "stop", args[0]
        self.modbusClient.WriteSingleRegister(0x050E, 1000, 1)
        prQueue.reset()

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
            holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x050E, 1,1)
            print('current Pr:'+str(holdingRegisters[0]))
            time.sleep(0.7)
    def save_pos_to_db_once(self,current_pos=None):
        if current_pos==None:
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
    # self.status={'mode':'controled','alarm':0,'ex_alarm':0,'position':-999,'home':'homed'}
    # self.status['ex_alarm'] = 
    #   1               |    2  |       4      |    8
    # modbus no response| tilted| partner alarm| partner dead
    def sendStatus(self):
        str_mapping={'controled':0,'autorun':1,'not_homed':0,'homed':1}
        while True:
            alarm=self.readAlarm()
            if readAlarm!=None:
                self.status['alarm']=alarm
                self.status['ex_alarm']=self.status['ex_alarm']&(~1) # clear modbus no response bit
            else:
                status=[self.ID,1,0]
                alarm=0
                self.status['ex_alarm']=self.status['ex_alarm']|1
            # blob_data = ID mode alarm ex_alarm position homeStatus
            blob_data=[self.ID,str_mapping[self.status['mode']],self.status['alarm'],self.status['ex_alarm'],self.status['position'],str_mapping[self.status['home']]]
            send_data_to_partner('status',blob_data)
            send_data_to_server('status',blob_data)
            time.sleep(1)
        # id alarm 
    # Read position of last time ,then set software endstop
    def readAlarm(self):
        try:
            holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0002, 2,1) # read alarm
            alarm=ConvertRegistersToDouble(holdingRegisters)
            return alarm
        except Exception,err:
            print('readAlarm err:')
            traceback.print_exc() 
            return None
    def clearAlarm(self):
        self.modbusClient.WriteSingleRegister(0x0002, 0,1) 

    def home(self):
        if(self.safe==False):
            print('not to home')
            return
        sync=self.partnerHomeSync()
        #sync=True
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
                self.modbusClient.WriteSingleRegister(0x030C, 0x00, 1) # Disable manual DI setting
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
                    self.modbusClient.WriteSingleRegister(0x050E, 1000, 1)
                    raise
                except:
                    #traceback.print_exc()
                    print(self.partner+':'+str(PORT)+'partner still sleep')
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
        # check server and partner
        while True: #remember to fix back
            partnerRUOK=checkHostAlive(self.partner)
            if(checkHostAlive(self.server) and partnerRUOK):
                self.safe=True
                return False
            else:
                print('safe checking failure, STOP motor')
                self.modbusClient.WriteSingleRegister(0x050E, 1000, 1) # Stop motor
                break
            time.sleep(5)
        # check modbus responses
        if(self.read_current_pos()==None):
            print('safety check failure: No modbus responses')
        else:
            return False

        print('safety pass')
        self.safe=True
        return True
    

    def moveMotor(self, howmany, speed, acc,Praddr,PrNum):
        print('-------------move to--------------')
        print('howmany='+str(howmany)+' pos='+str(self.posdmx[howmany]))
        motordistance = self.posdmx[howmany] #1000000
        speed=int(round(speed/16.0))-1
        acc=int(round(acc/16.0))-1
        # setting_val=0x00000023 | (acc<<8) |(acc<<12)|(speed<<16)
        # self.modbusClient.WriteMultipleRegisters(self.prQueue.nextPrSettingAddr, [motordistance & 0xFFFF, motordistance >> 16],1)
        # time.sleep(0.025)
        speedPr=0x00000032|(speed<<16)|(acc<<12)|(acc<<8) # speed + acc
        
        print('Pr_Addr='+str(hex(Praddr))+' x='+str(motordistance)+' speedPr='+str(hex(speedPr)))
        
        self.modbusClient.WriteMultipleRegisters(Praddr-2, [speedPr & 0xFFFF, speedPr >> 16],1) # Define Pr1~Pr49
        self.modbusClient.WriteMultipleRegisters(Praddr, [motordistance & 0xFFFF, motordistance >> 16],1)
        self.modbusClient.WriteSingleRegister(0x050E, PrNum, 1)
        #time.sleep(0.025)
    def set_acc(self,row,acc):
        print('set acc')
        if(row>16 or row <0 or acc==0):
            return
        if(acc>65500):
            acc=65500
        addr=0x0528+row*2
        self.modbusClient.WriteMultipleRegisters(addr, [acc & 0xFFFF, acc >> 16],1)
        time.sleep(0.025)
    def set_speed(self,row,speed):
        print('set speed')
        if(row>15 or row <0 or speed==0):
            return
        if(speed>65500):
            speed=65500
        addr=0x0578+row*2
        speed=speed*10
        self.modbusClient.WriteMultipleRegisters(addr, [speed & 0xFFFF, speed >> 16],1)
        time.sleep(0.025)
    def set_max_PUU(self,positivePUU,negtivePUU):
        negtivePUU=int32(negtivePUU)
        positivePUU=int32(positivePUU)
        self.modbusClient.WriteMultipleRegisters(0x0510, [positivePUU & 0xFFFF, positivePUU >> 16],1)
        self.modbusClient.WriteMultipleRegisters(0x0512, [negtivePUU & 0xFFFF, negtivePUU >> 16],1)
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
                        first_index=idx+(3*self.ID)-3
                        #print('first_index='+str(first_index)) 
                        if universe == 0 and ( rawbytes[first_index] != lastpos ):#or rawbytes[idx+self.ID] != lastspeed or rawbytes[idx+self.ID+1] != lastacc ):
                            #print ("1 %d 5 %d 7 %d 13 %d" % (lastpos , lastspeed, rawbytes[idx+9], rawbytes[idx+10]))
                            lastpos = rawbytes[first_index] # 3
                            lastspeed = rawbytes[first_index+1] # 4==ID
                            lastacc = rawbytes[first_index+2] # 5
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
    def start(self): 
        _thread.start_new_thread(self.motor_command_routine,())
        _thread.start_new_thread(self.artnet_handler,(self.sock,0))
        _thread.start_new_thread(self.send_pos,())
        _thread.start_new_thread(self.save_pos_to_db,())
        #self.run_Pr1()
        
    # Pop motor command and run
    def motor_command_routine(self):
        while True:
            
            #if(self.prQueue.queueLock is False):
            if(len(self.prQueue.move_list)>0):
                holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x050E, 1,1) # Which Pr number is running
                moveData=self.prQueue.move_list[0]
                #print('current Pr:'+str(holdingRegisters[0]))
                if(moveData[4]==holdingRegisters[0]):
                    print('------pass------')
                    continue
                #prQueue.queue_mutex.acquire()
                moveData=self.prQueue.move_list.pop(0)
                #prQueue.queue_mutex.release()
                self.moveMotor(moveData[0],moveData[1],moveData[2],moveData[3],moveData[4])
            time.sleep(0.01)
    def test(self):
        print('test')
        # holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0520, 2,1)
        # doubeVal=ConvertRegistersToDouble(holdingRegisters)
        # print('pos=',ctypes.c_long(doubeVal).value)
        # holdingRegisters = self.modbusClient.ReadHoldingRegisters(0x0002, 2,1)
        # print('alarm=',ConvertRegistersToDouble(holdingRegisters))
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
                self.modbusClient.WriteSingleRegister(0x030C, 0x00, 1) # Disable manual DI setting
                self.set_max_PUU(2147483647,-2147483648)
                break
        time.sleep(5)
        print('pos='+str(self.read_current_pos()))
    def jog(self,upOrdown,rpm=250):
        # Joggggggg
        self.modbusClient.WriteSingleRegister(0x040A, rpm, 1) # jog rpm
        if upOrdown=='D':
            self.modbusClient.WriteSingleRegister(0x040A, 4999, 1) # jgo down 4999
        else:
            self.modbusClient.WriteSingleRegister(0x040A, 4998, 1) # jgo down 4999
        #self.modbusClient.WriteSingleRegister(0x040A, 0, 1)
        while(True):
            try:
                print('jogging')
            except:
                self.modbusClient.WriteSingleRegister(0x040A, 0, 1)
                print('stop jogging')
                break
            

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
        val=0x00000032
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
        self.modbusClient.WriteSingleRegister(0x0172, 60,1) # Torque 60%
        self.modbusClient.WriteSingleRegister(0x023C, 5,1) # Disable EEPROM
        
class PrQueue():
    def __init__(self):
        #self.queueLock=False
        self.queue_mutex = threading.Lock()
        self.move_list=[]
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
        self.nextPrNum=self.nextPrNum+1
        if self.nextPrNum==4:
            self.nextPrNum=1
        if(49>self.nextPrNum>0):
            self.nextPrPathAddr = 0x0606+(self.nextPrNum-1)*4
            self.nextPrSettingAddr=self.nextPrPathAddr-2
        else:
            self.nextPrPathAddr = 0x0702+(self.nextPrNum-49)*4
            self.nextPrSettingAddr=self.nextPrPathAddr-2
    def reset(self):
        self.queue_mutex.acquire()
        self.nextPrNum=1
        self.nextPrPathAddr=0x0606
        self.nextPrSettingAddr=0x0604
        self.move_list[:] = []
        self.queue_mutex.release()
        #self.queueLock=False
    # def getPrPathAddr(self,nextPrNum):
    #     if(59>nextPrNum>0):
    #         return 0x0606+(nextPrNum-1)*4
    #     else:
    #         return 0x0702+(nextPrNum-59)*4
if __name__ == '__main__':
    print('Program started from')
    print(datetime.datetime.now())

    lockfile = '/home/pi/SonicStick/fcntl.lock'
    locked=False
    try:
        f = open(lockfile, 'r')
    except IOError:
        f = open(lockfile, 'wb')
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        unlock=True
    except:
        print('locked')

    if unlock:
        # Takes argument
        parser = argparse.ArgumentParser()
        parser.add_argument("--T", default="R")
        parser.add_argument("--R", default=250)
        args = parser.parse_args()

        bigStick=SonicStick()
        if args.T=='T': # test
            bigStick.safetyCheck()
            bigStick.settings()
            _thread.start_new_thread(bigStick.sendStatus,())
            bigStick.home()
            time.sleep(5) 
            bigStick.start() # Running forever  
            #bigStick.test() 
            #embed()
        elif args.T=='Z':
            print('start embed')
            holdingRegisters = bigStick.modbusClient.ReadHoldingRegisters(0x0002, 2,1) # read alarm
            embed()
            bigStick.modbusClient.WriteSingleRegister(0x0002, 0, 1) # clear alarm
        elif args.T=='U': # test
            bigStick.jog('U',int(args.R))
        elif args.T=='D': # test
            bigStick.jog('D',int(args.R))
        elif args.T=='R':
            bigStick.set_max_PUU(2147483647,-2147483648)
            bigStick.save_pos_to_db_once(2147483647)
            bigStick.DbObj.print_data()
        elif args.T=='A':
            for i in range(16):
                bigStick.set_acc(i,500*(16-i))
            bigStick.set_acc(0,12000)
            bigStick.set_acc(1,10000)
            time.sleep(3)
        elif args.T=='S':
            bigStick.set_speed(0,10)
            bigStick.set_speed(1,50)
            bigStick.set_speed(2,200) 
            bigStick.set_speed(3,300)
            bigStick.set_speed(4,400)
            bigStick.set_speed(5,500)
            bigStick.set_speed(6,600)
            bigStick.set_speed(7,700)
            bigStick.set_speed(8,800)
            bigStick.set_speed(9,900)
            bigStick.set_speed(10,1000)
            bigStick.set_speed(11,1100)
            bigStick.set_speed(12,1200)
            bigStick.set_speed(13,1300)
            bigStick.set_speed(14,1400)
            bigStick.set_speed(15,1500)
            time.sleep(3)
        else:
            # will be in start
            #bigStick.settings()
            #bigStick.start() # Running forever
            pass
        try:
            while True:
                now=time.time()
                # if(now-self.last_time>24.0):
                #     self.modbusClient.WriteSingleRegister(0x050E, 1000, 1)
                #     self.stopped=True
                #     self.prQueue.reset()
                #     self.last_time=time.time()
                #     for i in range(10):
                #         print('stop cause by timeout')
                time.sleep(0.1)
                pass
        except (KeyboardInterrupt, SystemExit):
            print('stop it')
            self.modbusClient.WriteSingleRegister(0x050E, 1000, 1)
    else:
        print('exit')




#!/usr/bin/env python
### CHANGELOG 
'''
2015-02-20
    setup the instrument for FAST data transfer mode
    added start and stop scan in FAST data transfer mode
2014-06-12
    reverted to stop_scan returning both channels
2014-05-21
    stop_scan returns only channelX
2014-03-12
    new read mode: check availability of data to read with spoll (query_data_available),
    then read data until end-of-string (read_to_end)
    added function to read buffer (query_data)
    added function checking if instrument is idle (is_idle)
2014-03-11
    added external trigger setting
'''
### TODO
''' '''
__version__ = '0.1'

###imports
import gpibprologix as plgx
import numpy as np
import sys
import time

DEBUG = False

class sr830:
    '''
    Stanford SR830 Lock in class
    '''
    def __init__(self, gpib, address):
        '''
        Initialize 53181A object with GBIP object
        '''
        self.gpib       = gpib
        self.address    = address

        self.oflt = ['10 us', '30 us', '100 us', '300 us', '1 ms', '3 ms', '10 ms', '30 ms', '100 ms', '300 ms', \
                        '1 s', '3 s', '10 s', '30 s', '100 s', '300 s', '1 ks', '3 ks', '10 ks', '30 ks']
        self.ofsl = ['6 dB/oct', '12 dB/oct', '18 dB/oct', '24 dB/oct']
        self.rmod = ['High Reserve', 'Normal', 'Low Noise']
        self.sens = ['2 nV', '5 nV', '10 nV', '20 nV', '50 nV', '100 nV', '200 nV', '500 nV', \
                        '1 uV', '2 uV', '5 uV', '10 uV', '20 uV', '50 uV', '100 uV', '200 uV', '500 uV', \
                        '1 mV', '2 mV', '5 mV', '10 mV', '20 mV', '50 mV', '100 mV', '500 mV', '1 V']
        '''self.check_if_alive()
        if not raise myException'''
        self.cls()
    
    '''def check_if_alive(self):
        ans = self.idn()
        time.sleep(1)
            if not ans:
                return(1)'''

    ### 2015-02-20
    def read(self):
        '''while True: # aspetta che l'interfaccia segnali la disponibilita' di qualcosa
            a = self.spoll()
            print a
            #if a == '19\r\n': break
            if a >= 16: # MAV asserted
                break'''
        self.gpib.serial.write('++read\n')
        s = self.gpib.serial.read(4)
        return s
        
    def start_scan_meas_and_send(self):
        self.ext_trig(True)
        self.gpib.send(self.address, "STRD\n")
        self.gpib.serial.write('++mode 0\n') # prologix in device mode
        self.gpib.serial.write('++lon 1\n') # listen-only mode
        time.sleep(1) # scan is started after 0.5 s - p. 5-18 SR830 User Manual

    def stop_scan_meas_and_send(self):
        self.ext_trig(False)
        self.gpib.serial.write('++lon 0\n') # disable listen-only mode
        self.gpib.serial.write('++mode 1\n') # prologix in controller mode

        time.sleep(0.2) # wait that everything is settled before returning
        # the stage will start to move when back to the calling program,
        # if trigger is still active other data will be transmitted
        
    def read_data_binary_meas_and_send(self, stringa):
        stringa = stringa.rstrip()
        x = []
        sx = []
        sy = []
        x = [str(ord(xx)) for xx in stringa]
        '''for i in range(len(stringa)):
            x.append([str(ord(xx)) for xx in stringa[i]])'''
        print 'x', x
        for i in range(0, len(x), 4):
            sx.append((int(x[i]) << 8) + int(x[i + 1]))
            sy.append((int(x[i + 2]) << 8) + int(x[i + 3]))
        sx = [xx if xx <= 2**15 - 1 else xx - 2**16 for xx in sx]
        sy = [xx if xx <= 2**15 - 1 else xx - 2**16 for xx in sy]
        return sx, sy

        '''
        # converts two HEX bytes - MSB first - to signed integer
        # input string consists of multiples of 4 bytes, two bytes for channel X followed by two bytes for channelY
        # print stringa # 7fffffff00008000
        stringa = [stringa[i:i+4] for i in range(0, len(stringa), 4)] # split string every two bytes
        print stringa
        # print stringa # ['7fff', 'ffff', '0000', '8000']
        stringa = [int(x, 16) for x in stringa] # convert hex to int
        # print stringa # [32767, 65535, 0, 32768]
        stringa = [x if x <= 2**15 - 1 else x - 2**16 for x in stringa] # two's complement if needed
        # print stringa # [32767, -1, 0, -32768]
        x = []
        y = []
        for i in range(0, len(stringa), 2): # extract x and y
            x.append(stringa[i])
            y.append(stringa[i + 1])
        # print x # [32767, 0]
        # print y # [-1, -32768]
        return x, y
        '''

    def set_myaddr(self, addr):
        self.address    = addr

    def convert(self, byte0, byte1, byte2):
        ''' convert SR830 reading from 4-bytes bynary to float '''
        self.byte0 = byte0
        self.byte1 = byte1
        self.byte2 = byte2
        m = self.byte0 + (self.byte1 << 8) # forms the 16 bits integer from the lowest two bytes
        m = self.twos_comp(m, 16)
        x = m*2**(self.byte2 - 124)
        return x
        
    def twos_comp(self, val, bits):
        """compute the 2's complement of int value val"""
        self.val = val
        self.bits = bits
        if( (self.val & (1 << (self.bits - 1))) != 0 ):
            self.val = self.val - (1 << self.bits)
        return self.val

    ### 2014-03-14
    def spoll(self):
        self.gpib.serial.write('++spoll\n')
        stringa = self.read_to_end()
        return stringa
    
    ### 2014-03-14
    def read_data(self):
        self.gpib.serial.write('++read\n')
        stringa = self.read_to_end()
        return stringa
        
    ### 2014-10-01
    def read_data_binary(self, npoints):
        bytes_to_read = 4*npoints
        self.gpib.serial.write('++read eoi\n')
        stringa = self.gpib.serial.read(bytes_to_read)
        #print 'in read_data_binary',stringa

        stringa = [stringa[i:i+4] for i in range(0, len(stringa), 4)] # qui forma una stringa tipo \x02\x00f\x00
        '''
        i dati vengono ricostruiti come stringa di stringhe lunghe 4 bytes
        '''
        boh = len(stringa)
        x = []
        for i in range(boh):
            x.append([str(ord(xx)) for xx in stringa[i]]) # forma una stringa tipo [['0', '0', '102', '0'],['234', '178', '108', '0']
        #print x
        
        xx = [self.convert(int(xxx[0]), int(xxx[1]), int(xxx[2])) for xxx in x]
        #print xx
        return xx
        
        
        '''
        #xx = self.convert(int(x[0]), int(x[1]), int(x[2]))
        l = range(len(x))
        for i in range(l):
        xx = [ for i in l[0::4]]
        print xx
        
        #return stringa
        return xx
        '''
        
    ### 2014-03-12
    def query_data_available(self):
        while True:
            if DEBUG:
                print '\t\t\tMAV?'
            stringa = self.spoll()
            if DEBUG:
                print '\t\t\t\tgot ' + str(stringa) + ' in query_data_available'
            try:
                if int(stringa) & (1 << 4) == 16: # 4th bit in Status Byte set, data available
                    if DEBUG:
                        print '\t\t\tMAV ok, exiting query_data_available'
                    break
            except ValueError:
                pass
        
    ### 2014-03-12
    def query_data(self):
        if DEBUG:
            print '\tstart data retrieving process...'
            print '\t\thow many points?'
        self.write('SPTS?') #self.gpib.send(self.address, 'SPTS?\n')
        self.query_data_available()
        if DEBUG:
            print '\t\tnow getting points'
        npoints = self.read_data()
        npoints = int(npoints)
        # print npoints
        if DEBUG:
            print '\t\t\tgot ' + str(npoints) + ' points in query_data'

        # bynary reading
        self.write('TRCL? 1,0,' + str(npoints))
        self.query_data_available()
        chX = self.read_data_binary(npoints)
        self.write('TRCL? 2,0,' + str(npoints))
        self.query_data_available()
        chY = self.read_data_binary(npoints) # last value is followed by a comma

        '''
        # ASCII reading
        self.write('TRCA? 1,0,' + str(npoints)) #self.gpib.send(self.address, 'TRCA? 1,0,' + str(npoints) + '\n')
        self.query_data_available()
        t0 = time.time()
        chX = self.read_data() # last value is followed by a comma
        print 'letto 1 canale in ascii in', time.time() - t0    
        #if DEBUG:
        #    print chX
        chX = [float(x) for x in chX.rsplit(',', 1)[0].split(',')] # make chX by removing last NULL (rsplit(',', 1)[0]) and then splitting again        
        self.write('TRCA? 2,0,' + str(npoints)) #self.gpib.send(self.address, 'TRCA? 1,0,' + str(npoints) + '\n')
        self.query_data_available()
        chY = self.read_data() # last value is followed by a comma
        chY = [float(x) for x in chY.rsplit(',', 1)[0].split(',')] # make chX by removing last NULL (rsplit(',', 1)[0]) and then splitting again        
        '''
        return chX, chY

    def re_read_binary(self):
        ''' DELETE this one '''
        self.write('SPTS?') #self.gpib.send(self.address, 'SPTS?\n')
        self.query_data_available()
        npoints = self.read_data()
        npoints = int(npoints)
        print npoints
        self.write('TRCL? 1,0,' + str(npoints))
        self.query_data_available()
        t0 = time.time()
        x = self.read_data_binary(npoints)
        print 'letto un canale in binario in', time.time() - t0
        self.write('TRCL? 2,0,' + str(npoints))
        self.query_data_available()
        y = self.read_data_binary(npoints) # last value is followed by a comma
        return x, y
        
    ### 2014-03-12
    def read_to_end(self):
        stringa = ''
        while True:
            s = self.gpib.serial.read(1)
            stringa += s
            #print a
            if s == '\n'and len(stringa) > 1:
                if DEBUG:
                    print 'read_to_end found newline...'
                break
        if DEBUG:
            print '...returning'
        return stringa.rstrip()
        
    '''### 2014-03-12
    def is_idle(self):
        while True:
            self.gpib.serial.write('++spoll\n')
            stringa = self.read_to_end()
            if int(stringa) & (1 << 2) == 2: # 2th bit in Status Byte set, no operation in progress
                break'''

    ### 2014-03-11    
    def write(self, command):
        self.gpib.send(self.address, command + '\n')
        
    ### 2014-03-11    
    def ext_trig(self, mode):
        self.write('TSTR ' + str(int(mode))) #self.gpib.send(self.address, 'TSTR ' + str(int(mode)) + '\n')
            
    ### 2014-03-11    
    def data_buffer_reset(self):
        self.write('REST') #self.gpib.send(self.address, 'REST\n')
            
    ### 2014-03-12
    def prepare_scan(self):
        self.data_buffer_reset()
        self.ext_trig(True)
        #self.write('STRT')
        
    ### 2014-03-12
    def stop_scan(self):
        #self.write('PAUS')
        if DEBUG:
            print 'scan paused'
        self.ext_trig(False)
        if DEBUG:
            print 'ext trigger disabled'
        chX, chY = self.query_data()
        return chX, chY
        '''
        chX = self.query_data()
        return chX
        '''
        
    def idn(self):
        '''
        Request identification string
        '''
        self.gpib.send(self.address, "*IDN?\n")
        self.gpib.read()
        time.sleep(0.1)
        return self.gpib.receive()
    
    def reading_nospoll(self, addr, wait=0):
        self.gpib.serial.write("++addr " + str(addr) + "\n")
        self.gpib.serial.write("++read eoi\n")
        
        if wait > 0:
            time.sleep(wait)

        #return float(self.gpib.receive())
        return self.gpib.receive()

    def read_configuration(self):
        self.cls()
        
        time.sleep(0.1)
        self.gpib.send(self.address, 'SENS?\n')
        time.sleep(0.1)
        self.gpib.out('++read eoi\n')
        #self.gpib.read()
        time.sleep(0.1)
        sensitivity = self.gpib.receive(False)
        sensitivity.rstrip()
        
        time.sleep(0.1)
        self.gpib.send(self.address, 'RMOD?\n')
        time.sleep(0.1)
        self.gpib.out('++read eoi\n')
        #self.gpib.read()
        time.sleep(0.1)
        reserve_mode = self.gpib.receive(False) #self.read_to_end_of_string()
        reserve_mode.rstrip()
        
        time.sleep(0.1)
        self.gpib.send(self.address, 'OFLT?\n')
        time.sleep(0.1)
        self.gpib.out('++read eoi\n')
        #self.gpib.read()
        time.sleep(0.1)
        time_constant = self.gpib.receive(False)
        time_constant.rstrip()
        
        time.sleep(0.1)
        self.gpib.send(self.address, 'OFSL?\n')
        time.sleep(0.1)
        self.gpib.out('++read eoi\n')
        #self.gpib.read()
        time.sleep(0.1)
        filter_slope = self.gpib.receive(False)
        filter_slope.rstrip()
        
        return self.sens[int(sensitivity)], self.rmod[int(reserve_mode)], \
                self.oflt[int(time_constant)], self.ofsl[int(filter_slope)]
    
    def read_to_end_of_string(self):
        a = ''
        while True: # aspetta che l'interfaccia segnali la disponibilita' di qualcosa
            self.gpib.serial.write('++spoll\n')
            a = self.gpib.serial.read(4)
            if a == '19\r\n': break
        self.gpib.serial.write('++read\n')
        stringa = ''
        while True:
            s = self.gpib.serial.read(1)
            stringa += s
            #print a
            if s == '\n'and len(stringa) > 1: break
        return stringa

    def read_XY(self, count):
        X = []
        Y = []
        ##self.gpib.send(self.address, 'STRT\n') # starts data storage
        ##self.gpib.send(self.address, 'SPTS ?\n') # queries buffered points
        ##n_points = self.gpib.read()measurement_delay
        ##time.sleep(0.2)
        ##print 'buffered points', n_points
        while count:
            while True: # aspetta che l'interfaccia segnali la disponibilita' di qualcosa
                self.gpib.serial.write('++spoll\n')
                a = self.gpib.serial.read(3)
                if a == '3\r\n': break
                # apparentemente, '1' indica nessun comando in esecuzione
                # '3' quando ha finito di far qualcosa
            self.gpib.send(self.address, 'SNAP ? 1,2\n') # Read the value of the CH1 display

            '''#print 'dato snap'
            continua = True
            while continua:
                self.gpib.serial.write("++spoll\n")
                a = self.gpib.serial.read(4)
                #print "a = ", a
                if float(a) == 19: # disponibile una misura
                    continua = False
                else:
                    continua = True'''

            while True: # aspetta che l'interfaccia segnali la disponibilita' di qualcosa
                self.gpib.serial.write('++spoll\n')
                a = self.gpib.serial.read(4)
                if a == '19\r\n': break
            self.gpib.serial.write('++read\n')
            
            #print 'mo vado'
            
            '''while True:
                a = ''
                self.gpib.serial.write('++spoll\n')
                while True:
                    s = self.gpib.serial.read(1)#50)
                    a += s
                    print a
                    if s == '\n'and len(a) > 1: break
                    time.sleep(0.01)
                if a.strip() == '3': break'''
                
            a = ''
            self.gpib.serial.write('++spoll\n')
            while True:
                s = self.gpib.serial.read(1)#50)
                a += s
                #print a
                if s == '\n'and len(a) > 1: break
            
            a = a.strip()
            #time.sleep(0.5)
            ###print self.gpib.receive()
            #print count
            count -= 1
            
            X.append(float(a.split(',')[0]))
            Y.append(float(a.split(',')[1]))
            
        #print np.mean(X), np.std(X, ddof = 1), np.mean(Y), np.std(Y, ddof = 1)
        return np.mean(X), np.std(X, ddof = 1), np.mean(Y), np.std(Y, ddof = 1)
        #return sum(X)/len(X), sum(Y)/len(Y) # returns the mean over counts
        '''
            s = self.gpib.receive()
            #s = self.gpib.read()
            time.sleep(0.2)
            print count, s
            X.append(s.split(',')[0])
            Y.append(s.split(',')[1])
            count -= 1
        ##self.gpib.send(self.address, 'SPTS ?\n') # queries buffered points
        ##n_points = self.gpib.read()
        
        ##print 'buffered points', n_points
        ##self.gpib.send(self.address, 'REST\n') # stops data storage and reset buffer
        return X, Y
        '''
        
    def reading(self, wait=0):
        self.gpib.send(self.address, "TRIG\n")
                
        continua = True
        while continua:
            self.gpib.serial.write("++spoll\n")
            a = self.gpib.serial.read(24)
            #print "a = ", a
            if float(a) == 3: #19?
                continua = False
            else:
                continua = True
        #print "Measurements finished"

        self.gpib.send(self.address, "OUTR? 1\n") # Read the value of the CH1 display

        self.gpib.read()
        
        if wait > 0:
            time.sleep(wait)
        
        modulus = float(self.gpib.receive())
        
        self.gpib.send(self.address, "OUTR? 2\n") # Read the value of the CH2 display

        self.gpib.read()
        
        if wait > 0:
            time.sleep(wait)
        
        phase = float(self.gpib.receive())
        
        return modulus, phase
        
    def setup(self):
        self.gpib.send(self.address, "DDEF 1,0,0\n") # Output CH1 X
        self.gpib.send(self.address, "DDEF 2,0,0\n") # Output CH2 Y
        self.gpib.send(self.address, "ISRC 0\n") # Channel A
        self.gpib.send(self.address, "ICPL 1\n") # DC Coupling
        self.gpib.send(self.address, "IGND 0\n") # Float
        self.gpib.send(self.address, "ILIN 3\n") # Line and 2xLine filters
        self.gpib.send(self.address, "FMOD 0\n") # Reference source external
        self.gpib.send(self.address, "RSLP 1\n") # Trigger TTL pos edge
        self.gpib.send(self.address, "SENS 19\n") # 5 mV    18\n") # 2mV   17\n") # 1 mV
        self.gpib.send(self.address, "RMOD 1\n") # Reserve Normal
        self.gpib.send(self.address, "OFLT 7\n") # Time constant 30 ms
        self.gpib.send(self.address, "SYNC 0\n") # Synchronous filter off
        #self.gpib.send(self.address, "OFSL 3\r\n") # Filter slope 24 dB
        self.gpib.send(self.address, "SRAT 14\n") # Sample rate: trigger
        ##self.gpib.send(self.address, 'TSTR 1\n') # TRIG starts the scan
        self.gpib.send(self.address, "SEND 0\n") # One shot measurement
        
        ### 2015-02-20
        self.gpib.send(self.address, "FAST 2\n") # set the instrument in fast mode.
        #                                       Data are transmitted as soon as they are acquired
        
        '''
        time.sleep(4)
        self.gpib.send(self.address, "SENS ?\r\n")
        self.gpib.read()
        time.sleep(0.04)
        a = self.gpib.receive()
        #return self.gpib.receive()
                
        print "Sensitivity set to: " + a #I1.split()[1]
        '''
        
    def rst(self):
        if self.gpib:
            print "Device reset"
            self.gpib.send(self.address, "*RST\n")
    
    def cls(self):
        if self.gpib:
            print "Interface reset"
            self.gpib.send(self.address, "*CLS\n")

    def clearSRE(self):
        if self.gpib:
            print "clear service request enable register"
            self.gpib.send(self.address, "*SRE 0\n") # ???????????????
            
    def clearESE(self):
        if self.gpib:
            print "clear event status enable register"
            self.gpib.send(self.address, "*ESE 0\n") # ????????????????'


if __name__ == "__main__":
    print "sto nel main"
    import gpib_SR830 as deviceclass
    
    if len(sys.argv) < 3:
        print "TEST SR830 CONNECTED TO PROLOGIX LAN/USB-GPIB INTERFACE"
        print "Usage: gpib_SR830.py <GPIB ADDRESS> <ip=ADDRESS | com=SERIAL PORT> [debug]"
        exit()

    else:
        debugmode = False
        if len(sys.argv) > 3:
            debugmode = (sys.argv[3].upper() == "DEBUG")
                
        if sys.argv[2].upper()[0:3] == "IP=":   # USE LAN-GPIB INTERFACE
            param = sys.argv[2].upper()[3:]
            gpib = plgx.prologix(ip=param, debug=debugmode)
            
        elif sys.argv[2].upper()[0:4] == "COM=":# USE USB-GPIB INTERFACE
            #param = sys.argv[2].upper()[4:]
            param = sys.argv[2][4:]
            gpib = plgx.prologix(comport=param, debug=debugmode)
            
        else:
            print "Unknown parameter: " + sys.argv[2]
            exit()

        device = deviceclass.k2182a(gpib, sys.argv[1])
        
        
        print "Testing SR830 class"
        print "Waiting for instrument ...\n"

        #device.rst()
        #time.sleep(1)
        #print device.idn()
        device.setup()
        try:
            while True:
                print device.reading()
                time.sleep(1)
        except KeyboardInterrupt:
            Running = False
        except:
            gpib.close()
        exit()

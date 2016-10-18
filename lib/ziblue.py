#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import serial
import time
import traceback

PORT = '/dev/rfplayer' # Linux with UDEV rule
#PORT = 'COM3'  # Windows
RFPLAYER_ID = "ZIA--Welcome to Ziblue Dongle 433/868Mhz!"

# Due to windows connect issue, try to close serial before. Don't work each time
if PORT.find('COM') != -1 :
    ZiBlue = serial.Serial()
    ZiBlue.port= PORT
    ZiBlue.baudrate  = 115200
    ZiBlue.close()

identifier = ["Z","I","A","3","3"]

try :
    ZiBlue = serial.Serial(PORT, 115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE, timeout=2, xonxoff=0, rtscts=1, dsrdtr =None)

    print(u"Write {0} bytes.".format(ZiBlue.write(b'ZIA++HELLO\r')))
    id = ZiBlue.readline()
    if id.find(RFPLAYER_ID) != -1 :
        print(u"RFPLAYER FIND : {0}".format(id))
    else:
        print(u"Bad identification: {0}".format(id))
    print(u"Write {0} bytes.".format(ZiBlue.write(b'ZIA++FORMAT JSON\r')))
    print(u"Get Status ...")
    print(u"Write {0} bytes.".format(ZiBlue.write(b'ZIA++STATUS JSON\r')))
    status = {}
    while buffer : # Read all lines of status out
        buffer = ZiBlue.readline()
        if buffer[:6].find("ZIA--") != -1 :
            try :
                status.update(json.loads(buffer[6:]))
            except:
                print(traceback.format_exc())
                print(u"RFP1000 bad status {0}".format(buffer[6:]))

    print  status
#    print(st)
    print(u"*************************************************")
    print(u"Start sniff RFPLAYER on {0}.....".format(PORT))
    print(u"*************************************************")
    while True :
        dataOK = False
        buffer = ZiBlue.readline()
        if buffer :
            try :
                offset = 1
#                i = 0
#                for d in buffer :
#                    print d, identifier[i]
#                    if d == identifier[i] :
#                        i +=1
#                        if i == len(identifier):
#                            dataOK = True
#                            print(u"IDENTIFIED HEADER")
#                            break
#                    offset +=1

                if buffer[:5]=="{0}{1}{2}".format('ZI', 'A','33') != -1 :
                    dataOK = True
                    offset = 5
                    print(u"IDENTIFIED HEADER")
                print(u"Header ({0}): {1}".format(offset, buffer[:offset]))
                if dataOK :
                    data = json.loads(buffer[offset:])
                    print(u"{0} : {1}".format(type(data), data))
            except:
                print(traceback.format_exc())
                pass
        if not dataOK: print(u"{0} size {1} : {2}".format(type(buffer), len(buffer), buffer))
        time.sleep(0.5)
except :
    print(u"Interrupt ....")
    print(traceback.format_exc())
    ZiBlue.close()

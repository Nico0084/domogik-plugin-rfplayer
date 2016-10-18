#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

The dongle RFPLAYER RFP1000 is a new generation Radio Frequency device. The RFP1000 looks like a USB
key with 2 independent Radio Frequency transceivers 433 Mhz and 868 Mhz dedicated to a Home Automation
usage.

Implements
==========

- RF 433 Mhz and 868 Mhz
- bidirectional radio GATEWAY
- REPEATER
- protocols VISONIC, CHACON/DIO, DOMIA, X10, DELTADORE, SOMFY, BLYSS (433Mhz), KD101, PARROT, Scientific Oregon, OWL

@author: Nico <nico84dev@gmail.com>
@copyright: (C) 2007-2016 Domogik project
@license: GPL(v3)
@organization: Domogik
"""


import json
import serial
import time
import traceback
from serial_rfplayer import SerialRFPlayer

class SerialRFP1000(SerialRFPlayer):
    """Base class to handle RFPLAYER on serial port"""

    def __init__(self, log, stop, rfp_device, cb_receive, cb_register_thread,
                 baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE, timeout=0.1, xonxoff=0, rtscts=1, dsrdtr=None, fake_device=None):
        """ Init An RFP1000 device and start communication.
            @param log : log instance
            @param stop : stop Event
            @param rfp_device : rfplayer device (ex : /dev/rfplayer)
            @param cb_receive : callback when data received.
            *** next parameters are optional and should be changed only by an expert and an informed choice ***
            @param cb_register_thread : callback register all daemon thread.
            @param baudrate : optional serial port baudrate. Default: 115200 bauds
            @param bytesize : optional serial port bytesize. Default: serial.EIGHTBITS
            @param parity : optional serial port parity. Default: serial.PARITY_NONE
            @param stopbits : optional serial port stopbits. Default: serial.STOPBITS_ONE
            @param timeout : optional serial port timeout on read. Default: 1s
            @param xonxoff : optional serial port flow control xonxoff. Default: disabled (0)
            @param rtscts : optional serial port hardware flow control rtscts. Default: unable (1)
            @param dsrdtr : optional serial port hardware flow control rtscts. Default: disabled (None)
            @param fake_device : optional fake device. If None, this will not be used. Else, the fake serial device library will be used. Default: None
        """
        self._sendMessage = cb_receive
        self.status = {}
        SerialRFPlayer.__init__(self, log, stop, rfp_device, self.handle_msg, cb_register_thread, baudrate, bytesize, parity, stopbits, timeout, xonxoff, rtscts, dsrdtr, fake_device)

    @property
    def RFP_Id(self):
        """ Get value returned by HELLO command"""
        return "ZIA--Welcome to Ziblue Dongle 433/868Mhz!"

    def open(self):
        """ Open serial com and start communication."""
        if SerialRFPlayer.open(self) :
            self.start_services()
            self.getStatus()
            return True
        else :
            return False

    def getStatus(self):
        """ Send a STATUS command to rfplayer"""
        if  self.rfPlayer is not None :
            self.log.info(u"Get Status of {0}".format(self.RFP_device))
            self.send_to_RFP('STATUS JSON', True, self.setStatus)

    def setStatus(self, data):
        """ Decode Status data from RFP100 JSON """
        if 'ackFor' in data and data['ackFor']['command'] == 'STATUS JSON' :
            self.status = {}
            self.log.debug(u"RFP1000 {0} receive STATUS result".format(self.RFP_device))
        else:
            self.log.debug(u"RFP1000 {0} receive complement STATUS".format(self.RFP_device))
        if 'systemStatus' in data :
            self.status['systemStatus'] = data['systemStatus']
        if 'radioStatus' in data :
            self.status['radioStatus'] = data['radioStatus']

    def handle_msg(self, msg):
        """Handle msq to MQ"""
        if "radioStatus" in msg :
            self.setStatus(msg)
            return
        if "systemStatus" in msg :
            self.setStatus(msg)
            return
        self.log.debug("Sending to 0MQ : {0}".format(msg))
        self._sendMessage(msg)

if __name__ == "__main__":
    import logging
    import threading
    import sys

    FORMAT = '%(asctime)s %(name)s %(levelname)s %(message)s'

    logging.basicConfig(filename='RFP1000-Test.log', level=logging.DEBUG, format=FORMAT)

    outLog = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(FORMAT)
    outLog.setFormatter(formatter)
    logging.getLogger().addHandler(outLog)
    logging.getLogger().setLevel(logging.DEBUG)
    log = logging.getLogger()

    stop = threading.Event()

    print logging
    print stop

    def fake_registerThread(th):
        print(u"{0} Registered :)".format(th))

    def fake_MQSending(msg):
        print(u"****** Message transmit to 0MQ : {0}\n".format(msg))

    RFP = SerialRFP1000(logging, stop, '/dev/rfplayer', fake_MQSending, fake_registerThread)
    if RFP.open():
        try :
            while True :
                time.sleep(0.2)
        except :
            stop.set()
            print(traceback.format_exc())
            print("********** END ************")

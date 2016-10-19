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
import os
import traceback
from threading import Thread, Lock
from Queue import Queue, Empty, Full

PORT = '/dev/rfplayer' # Linux with UDEV rule
#PORT = 'COM3'  # Windows

# Due to windows connect issue, try to close serial before. Don't work each time
if PORT.find('COM') != -1 :
    ZiBlue = serial.Serial()
    ZiBlue.port= PORT
    ZiBlue.baudrate  = 115200
    ZiBlue.close()


class SerialRFPlayer(object):
    """Base class to handle RFPLAYER on serial port"""

    HEADSIZE = 5
    SYNC_ID = 'ZI'
    SDQ_ASCII = 'A'
    SDQ_BIN = 'O'
    Q_CMD = '++'
    Q_REP = '--'
    Q_XML = '22'
    Q_JSON = '33'
    Q_TXT = '44'

    def __init__(self, log, stop, RFP_device, cb_receive, cb_register_thread,
                 baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE, timeout=2, xonxoff=0, rtscts=1, dsrdtr=None, fake_device=None):
        """ Init Serial com base
            @param log : log instance
            @param stop : stop Event
            @param RFP_device : rfplayer device (ex : /dev/rfplayer)
            @param cb_receive : callback when data received.
            *** next parameters are optional and should be changed only by an expert and an informed choice ***
            @param cb_register_thread : callback register all daemon thread.
            @param baudrate : optional serial port baudrate. Default: 115200 bauds
            @param bytesize : optional serial port bytesize. Default: serial.EIGHTBITS
            @param parity : optional serial port parity. Default: serial.PARITY_NONE
            @param stopbits : optional serial port stopbits. Default: serial.STOPBITS_ONE
            @param timeout : optional serial port timeout on read. Default: 2s
            @param xonxoff : optional serial port flow control xonxoff. Default: disabled (0)
            @param rtscts : optional serial port hardware flow control rtscts. Default: unable (1)
            @param dsrdtr : optional serial port hardware flow control rtscts. Default: disabled (None)
            @param fake_device : optional fake device. If None, this will not be used. Else, the fake serial device library will be used. Default: None
        """
        self.log = log
        self.stop = stop
        self.RFP_device = RFP_device
        self._cb_receive = cb_receive
        self._cb_register_thread = cb_register_thread
        self.fake_device = fake_device
        self.rfPlayer = None
        self.status = {}
        self._waiting_for_reponse = False
        self._dataFormat = self.Q_TXT

        # Queues for writing and receiving packets to/from Rfxcom
        self.RFP_Lock = Lock()
        self.write_RFP = Queue()
        self.RFP_received = Queue()
        # request command id, increase at each request
        self._reqNum = 0
        # Serial port config
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self.dsrdtr = dsrdtr

    @property
    def RFP_Id(self):
        """ Get value returned by HELLO command"""
        return "Not defined"

    @property
    def RFP_type(self):
        """ Get RFP type from pyhon class."""
        return self.__class__.__name__

    @property
    def RFP_FirmWare_Id(self):
        """ Get value returned by HELLO command"""
        return "File Download is done!"

    def getHeaderData(self, data):
        """ Return header type of packet
              @param data: raw data from serial RFPlayer
              @return : header dict type : {
                        Sync: True/False if RFPLayer ID detected
                        SDQ: SourceDestQualifier get if data formet ASCII or BINARY
                        Qualifier: Data format type XML, JSON, TEXT if ASSCI else len of Bytes.
                        pos: First data index, to get data without header
                        }
        """
        header = {'Sync': False, 'SDQ': '',  'Qualifier':'', 'pos': self.HEADSIZE}
#        print(u"Decode header of :{0}".format(data))
        if data[:self.HEADSIZE]=="{0}{1}{2}".format(self.SYNC_ID, self.SDQ_ASCII, self.Q_REP) :
            header.update({'Sync': True, 'SDQ': self.SDQ_ASCII,  'Qualifier': self.Q_REP})
        elif data[:self.HEADSIZE]=="{0}{1}{2}".format(self.SYNC_ID, self.SDQ_ASCII, self.Q_JSON) :
            header.update({'Sync': True, 'SDQ': self.SDQ_ASCII,  'Qualifier': self.Q_JSON})
        elif data[:self.HEADSIZE]=="{0}{1}{2}".format(self.SYNC_ID, self.SDQ_ASCII, self.Q_XML) :
            header.update({'Sync': True, 'SDQ': self.SDQ_ASCII,  'Qualifier': self.Q_XML})
        elif data[:self.HEADSIZE]=="{0}{1}{2}".format(self.SYNC_ID, self.SDQ_ASCII, self.Q_TXT) :
            header.update({'Sync': True, 'SDQ': self.SDQ_ASCII,  'Qualifier': self.Q_TXT})
        elif data[:self.HEADSIZE]=="{0}{1}{2}".format(self.SYNC_ID, self.SDQ_BIN, self.Q_REP) :
            header.update({'Sync': True, 'SDQ': self.SDQ_BIN,  'Qualifier': self.Q_REP})
        elif data[:self.HEADSIZE]=="{0}{1}{2}".format(self.SYNC_ID, self.SDQ_BIN, self.Q_JSON) :
            header.update({'Sync': True, 'SDQ': self.SDQ_BIN,  'Qualifier': self.Q_JSON})
        elif data[:self.HEADSIZE]=="{0}{1}{2}".format(self.SYNC_ID, self.SDQ_BIN, self.Q_XML) :
            header.update({'Sync': True, 'SDQ': self.SDQ_BIN,  'Qualifier': self.Q_XML})
        elif data[:self.HEADSIZE]=="{0}{1}{2}".format(self.SYNC_ID, self.SDQ_BIN, self.Q_TXT) :
            header.update({'Sync': True, 'SDQ': self.SDQ_BIN,  'Qualifier': self.Q_TXT})
        return header

    @property
    def isOpen(self):
        """ Get RFPLAYER header for json data"""
        return True if self.rfPlayer is not None else False

    def open(self):
        """ Open serial com."""
        if self.rfPlayer is None :
            try :
                if self.fake_device != None:
                    pass
                else:
                    self.rfPlayer = serial.Serial(self.RFP_device, self.baudrate, self.bytesize, self.parity,
                                                               self.stopbits, self.timeout, self.xonxoff, self.rtscts, self.dsrdtr)
                    with self.RFP_Lock:
                        self.rfPlayer.reset_output_buffer()
                        self.rfPlayer.write(b'ZIA++HELLO\r')
                        id = self.rfPlayer.readline()
                    if id.find(self.RFP_Id) != -1 :
                        self.log.info(u"{0} {1} CONNECTED : {2}".format(self.RFP_type, self.RFP_device, id))
                        self.set_JSON_Format()
                        return True
                    else:
                        self.log.error(u"{0} {1} Bad identification : {2}".format(self.RFP_type, self.RFP_device, id))
                        self.close()
            except :
                self.rfPlayer = None
                self.log.error(u"Error while opening {0} device {1} (disconnected ?) : {2}".format(self.RFP_type, self.RFP_device, traceback.format_exc()))
                self.close()
        else :
            self.log.warning(u"{0} device {1} allready open".format(self.RFP_type, self.RFP_device))
        return False

    def close(self):
        """ close serial com
        """
        self.log.info(u"Close {0} on {1}".format(self.RFP_type, self.RFP_device))
        try:
            self.rfPlayer.close()
        except:
                self.log.error(u"Error while closing {0} device {1} (disconnected ?) : {2}".format(self.RFP_type, self.RFP_device, traceback.format_exc()))
        self.rfPlayer = None

    def start_services(self):
        """ Start all daemon service in threads"""
        liste_process = Thread(None,
                             self.listen_RFP,
                             "ListenRFP",
                             (),
                             {})
        self._cb_register_thread(liste_process)
        liste_process.start()
        write_process = Thread(None,
                             self._daemon_queue_write,
                             "write_packets_process",
                             (),
                             {})
        self._cb_register_thread(write_process)
        write_process.start()
        read_process = Thread(None,
                             self._daemon_queue_read,
                             "Read_Queue_recept",
                             (),
                             {})
        self._cb_register_thread(read_process)
        read_process.start()
        # Sleep to get all service started
        self.stop.wait(1)

    def set_XML_Format(self):
        """ Set RFPlayer in XML data format"""
        self.send_to_RFP('FORMAT XML', False)
        self._dataFormat = self.Q_XML

    def set_JSON_Format(self):
        """ Set RFPlayer in JSON data format"""
        self.send_to_RFP('FORMAT JSON', False)
        self._dataFormat = self.Q_JSON

    def set_TXT_Format(self):
        """ Set RFPlayer in TEXT data format"""
        self.send_to_RFP('FORMAT TEXT', False)
        self._dataFormat = self.Q_TXT

    def _read_RFP_data(self):
        """ Read data from serial RFPlayer and put it in Queue.
              Packet data must have RFPlayer 'ZI' header sync to be validate and queuing.
        """
        if not self._waiting_for_reponse :
            if self.isOpen :
                try :
                    with self.RFP_Lock:
#                        self.log.debug(u"Serial read Listen")
                        buffer = self.rfPlayer.readline()
                        if buffer != "" :
                            if buffer[0] == '\r' :  # new line remove it
                                buffer = buffer[1:]
                        if buffer != "" and len(buffer) > self.HEADSIZE:
                            header = self.getHeaderData(buffer)
                            if header['Sync']:
                                index = buffer.find('reqNum')
                                if index != -1 :
                                    reqNum = self.getReqNum(buffer[self.HEADSIZE:])
                                    if reqNum != 0 : print(u"****** A ReqNum is find in data : {0}".format(reqNum))
                                self.log.debug(u"Queuing for {0} data received : {1}".format(self.RFP_device, buffer))
                                self.RFP_received.put_nowait({'header': header, 'data': buffer[self.HEADSIZE:]})
                except serial.SerialException:
                    self.log.error(u"Error while reading {0} device {1} (disconnected ?) : {2}".format(self.RFP_type, self.RFP_device, traceback.format_exc()))
                    self.close()
                except :
                    self.log.warning(u"Error on read {0} : {1}".format(self.RFP_device, traceback.format_exc()))

    def wait_RFP_response(self, ackFor, timeOut = 5):
        """ Wair for a response at RFPlayer request/command.
            Lock flow read until reponse or timeout.
            @param ackFor : Command source info {'command': the command sended, 'id': timestamp at send}
            @param timeOut : time to exit if no reponse. Default 5s
        """
        if self.isOpen :
            exitTimeOut = False
            endTime = time.time() + timeOut
            while not exitTimeOut and not self.stop.isSet():
                try :
                    buffer = self.rfPlayer.readline()
                    if buffer != "" :
                        if buffer[0] == '\r' :  # new line remove it
                            buffer = buffer[1:]
                    if buffer != "" and len(buffer) > self.HEADSIZE :
                        header = self.getHeaderData(buffer)
                        if header['Sync'] :
                            if header['Qualifier'] == self.Q_REP :
                                if len(buffer[self.HEADSIZE:]) > 2: # some Q_REP have no data !
                                    index = buffer.find('reqNum')
                                    if index != -1 :
                                        reqNum = self.getReqNum(buffer[self.HEADSIZE:])
                                        if reqNum == ackFor['reqNum'] :
                                            self.log.debug(u"Queuing for {0} response reqNum {1} : {2}".format(self.RFP_device, reqNum, buffer))
                                            self.RFP_received.put_nowait({'header': header, 'data': buffer[self.HEADSIZE:], 'ackFor': ackFor})
                                            return True
                                    else :
                                        if ackFor['command'] == 'UPDATE FIRMWARE' : # In case no reqNum, must be end off download.
                                            self.log.debug(u"Queuing for {0} response download firmware : {1}".format(self.RFP_device, buffer))
                                            self.RFP_received.put_nowait({'header': header, 'data': buffer[self.HEADSIZE:], 'ackFor': ackFor})
                                            return True
                                    self.log.debug(u"Data response received on {0} Without reqNum, not the one we wait. Nevertheless queuing :{1}".format(self.RFP_device, buffer))
                                    self.RFP_received.put_nowait({'header': header, 'data': buffer[self.HEADSIZE:]})
                                else :
                                    print(u" *********** No data **********")
                            else :
                                self.log.debug(u"Data received on {0} Not reponse type the one we wait. Nevertheless queuing :{1}".format(self.RFP_device, buffer))
                                self.RFP_received.put_nowait({'header': header, 'data': buffer[self.HEADSIZE:]})
                except serial.SerialException:
                    self.log.error(u"Error while reading {0} device {1} (disconnected ?) : {2}".format(self.RFP_type, self.RFP_device, traceback.format_exc()))
                    self.close()
                except :
                    self.log.warning(u"Error on read {0} for reponse: {1}".format(self.RFP_device, traceback.format_exc()))
                if time.time() >= endTime : exitTimeOut = True
            self.log.debug(u"Exit on timeOut {0}s for reponse :{1}\n{2}".format(self.RFP_device, ackFor, traceback.format_exc()))
        return False

    def _write_RFP_data(self, data):
        """ Write a packet data to RFPlayer
            @param data : the ASCII data to send.
        """
        if self.isOpen :
            try:
                self.rfPlayer.write(b'{0}{1}'.format(data, '\r'))
            except serial.SerialException:
                self.log.error(u"Error while writing on {0} device {1} (disconnected ?) : {2}".format(self.RFP_type, self.RFP_device, traceback.format_exc()))
                self.close()

    def _daemon_queue_write(self):
        """ Listen send Queue, write on RFPlayer and wait for reponse if nessecary.
        """
        self.log.info(u"***** Start write daemon Queue {0} on {1} *****".format(self.RFP_type, self.RFP_device))
        # infinite
        while not self.stop.isSet():
            # Wait for a packet in the queue
            try:
                data = self.write_RFP.get(block = True, timeout = 2)
            except Empty:
                continue
            self._waiting_for_reponse = True if data['response'] else False
            with self.RFP_Lock:
                self.log.debug(u"Send request {0} on {1} {2}".format(data['data'], self.RFP_type, self.RFP_device))
                self._write_RFP_data(data['data'])
                if data['response'] :
                    self.wait_RFP_response(data['ackFor'])
#                    print(u"----------- wait terminate {0} -------------".format(data['ackFor']['command']))
            self._waiting_for_reponse = False
        self.log.info(u"***** Write daemon Queue {0} on {1} stopped *****".format(self.RFP_type, self.RFP_device))

    def _daemon_queue_read(self):
        """ Listen receive Queue, call calback registered.
        """
        self.log.info(u"***** Start receive daemon Queue {0} on {1} *****".format(self.RFP_type, self.RFP_device))
        # infinite
        while not self.stop.isSet():
            # Wait for a packet in the queue
            try:
                data = self.RFP_received.get(block = True, timeout = 2)
            except Empty:
                continue
#            print(u"----- Data Queue receive : {0}".format(data))
            if data['header']['Qualifier'] == self.Q_REP:
                msg = self.decode_data(data['data'])
                if msg != {}:
                    if 'ackFor' in data :
                        if data['ackFor']['callback']is not None :
                            data['ackFor']['callback'](msg['data'], data['ackFor']['command'])
                        else :
                            if self._cb_receive is not None: self._cb_receive(msg['data'])
                    else :
                        if self._cb_receive is not None: self._cb_receive(msg['data'])
            elif self._cb_receive is not None :
                if data['header']['Qualifier'] == self.Q_XML:
                    msg = self.decode_XML(data['data'])
                    if msg != {}:
                        self._cb_receive(msg)
                elif data['header']['Qualifier'] == self.Q_JSON:
                    msg = self.decode_JSON(data['data'])
                    if msg != {}:
                        self._cb_receive(msg)
                elif data['header']['Qualifier'] == self.Q_TXT:
                    msg = self.decode_TEXT(data['data'])
                    if msg != {}:
                        self._cb_receive(msg)
        self.log.info(u"***** Receive daemon Queue {0} on {1} stopped *****".format(self.RFP_type, self.RFP_device))

    def listen_RFP(self):
        """ Start listening to RFPlayer forever.
        """
        self.log.info(u"***** Start listening {0} on {1} *****".format(self.RFP_type, self.RFP_device))
        # infinite
        while not self.stop.isSet():
                self._read_RFP_data()
        self.log.info(u"***** listening {0} on {1} stopped *****".format(self.RFP_type, self.RFP_device))

    def send_to_RFP(self, command, response=False, callback = None):
        """ Put in queue a command to send to RFPLAYER
             @param command : the command in ASCII
             @param response : True to wait for a response else False (default)
             @param callback : Fonction to be called at response received.
        """
        cmd = "{0}{1}{2}".format(self. SYNC_ID, self.SDQ_ASCII, self.Q_CMD)
        if response :
            self._reqNum += 1
            cmd += "{0}".format(self._reqNum)
            ackFor = {'command': command, 'reqNum': self._reqNum,  'callback': callback}
        else :
            ackFor = {}
        cmd +=" {0}".format(command)
        self.write_RFP.put_nowait({'data': cmd, 'response': response, 'ackFor': ackFor})

    def update_firmware(self, firmFile):
        """ Send a new firmware to RFPLAYER
            lock all request during process who take 2mins.
            @parm firmFile : firmware file location
        """
        if os.path.isfile(firmFile) :
            if self.isOpen :
                try:
                    with self.RFP_Lock:
                        self.log.info(u"Start Update firmware on {0} device {1} File {2}, Wait ...".format(self.RFP_type, self.RFP_device, firmFile))
                        lines = open(firmFile,"rb").readlines()
                        nbLines = len(lines)
                        n = 0
                        i = 0
                        step =[x for x in range(0,111, 10)]
                        for l in lines:
                            self.rfPlayer.write(l)
                            n += 1
                            progress = int(round( (n / float(nbLines)) * 100))
                            if progress == step[i]:
                                i += 1
                                self.log.info(u"Update firmware download {0}%".format(progress))
                        self.log.info(u"Update firmware on {0} device {1} File downloaded, Wait for internal check ...".format(self.RFP_type, self.RFP_device))
                        self.wait_RFP_response({'command': 'UPDATE FIRMWARE', 'reqNum': 0, 'callback': self.validate_UpdFirmware}, 80)
                except serial.SerialException:
                        self.log.error(u"Error while update firmware on {0} device {1} (disconnected ?) : {2}".format(self.RFP_type, self.RFP_device, traceback.format_exc()))
                        self.close()
        else :
            self.log.warning(u"Update firmware on {0} device {1} fail : File {2} not exist.".format(self.RFP_type, self.RFP_device, firmFile))

    def validate_UpdFirmware(self, data, ack=''):
        """ Check if message return after firmware update is ok, called by callback request.
            @param data: data formated in JSON
            @param ack: source request, empty if not an ack.
        """
        if data.find(self.RFP_FirmWare_Id) != -1 :
                self.log.info(u"Update firmware on {0} device {1} : {2}".format(self.RFP_type, self.RFP_device, data))
                self.close()
                self.log.info(u"Update firmware, wait reboot {0}s ...".format(60))
                self.stop.wait(60) # wait for RFP reboot
                if SerialRFPlayer.open(self) :
                    self.getStatus()
        else :
            self.log.warning(u"Update firmware on {0} device {1} fail : {2}".format(self.RFP_type, self.RFP_device, data))

    def getStatus(self):
        """ Send a STATUS command to rfplayer. Must be overwrited."""
        return {}

    def setStatus(self, data, ack):
        """ Set STATUS from rfplayer.  Must be overwrited.
            @param data: data formated in JSON
            @param ack: source request, empty if not an ack.
        """
        pass

    def getReqNum(self, packet):
        """ Extract RefNum from data (JSON)"""
        # TODO : Handle data XML and TEXT, if this proves useful ?
        data = self.decode_JSON(packet)
        for k in data :
            for k2 in data[k] :
                if k2 == 'reqNum' : return int(data[k][k2])
        return 0

    def decode_data(self, data):
        """ Find and decode response from RFPLAYER
             @param data : data that could parse in JSON
             @return : data in JSON format
        """
        msg = self.decode_JSON(data)
        if msg != {} : return {"type": self.Q_JSON, 'data': msg}
        msg = self.decode_XML(data)
        if msg != {} : return {"type": self.Q_XML, 'data': msg}
        msg = self.decode_TEXT(data)
        return {"type": self.Q_TXT, 'data': msg}

    def decode_JSON(self, data):
        """ Try JSON decode response from RFPLAYER
             @param data : data that could parse in JSON
             @return : data in JSON format
        """
        retval = {}
        if len(data) > 2 :
            try :
                retval = json.loads(data)
    #            print(u" ******* Data JSON decode OK ********")
            except :
                pass
#                self.log.error(u"{0} on {1} fail decode JSON :{2} \n{3}".format(self.RFP_type, self.RFP_device, data, traceback.format_exc()))
        return retval

    def decode_XML(self, data):
        """ Try XML decode response from RFPLAYER
             @param data : data that could parse in XML
             @return : data in SJON format
        """
        # TODO : Handle data XML, if this proves useful ?
        retval ={}
        try :
            retval = json.loads(data)
#            print(u" ******* Data XML decode OK ********")
        except :
            pass
#            self.log.error(u"{0} on {1} fail decode XML :{2} \n{3}".format(self.RFP_type, self.RFP_device, data, traceback.format_exc()))
        return retval

    def decode_TEXT(self, data):
        """ Try TEXT decode response from RFPLAYER
             @param data : data that could parse in TEXT
             @return : data in JSON format
        """
        # TODO : Handle data TXT, useful for some result command
        retval = ""
        try :
            retval = data
            print(u" ******* Data TEXT decode OK ********")
        except :
            pass
#            self.log.error(u"{0} on {1} fail decode TXT :{2} \n{3}".format(self.RFP_type, self.RFP_device, data, traceback.format_exc()))
        return retval

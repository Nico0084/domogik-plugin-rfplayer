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
import domogik.tests.common.testserial as testserial
import time
import os
import traceback
from threading import Thread, Lock
from Queue import Queue, Empty

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
    Q_REP = '--'    # Synchronous answers of the commands interpreter
    Q_HEX = '00'    # Asynchronous received RF Frames. Enabled by “FORMAT HEXA”
    Q_HEXF = '11'   # Asynchronous received RF Frames. Enabled by “FORMAT HEXA FIXED”
    Q_XML = '22'    # Asynchronous received RF Frames. Enabled by “FORMAT XML”
    Q_JSON = '33'   # Asynchronous received RF Frames. Enabled by “FORMAT JSON”
    Q_TXT = '44'    # Asynchronous received RF Frames. Set by “FORMAT TEXT”

    def __init__(self, manager, RFP_device, cd_handle_RFP_Data,
                 baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE, timeout=2, xonxoff=0, rtscts=1, dsrdtr=None, fake_device=None):
        """ Init Serial com base
            @param manager : RFPManager instance
            @param RFP_device : rfplayer device (ex : /dev/rfplayer)
            @param cd_handle_RFP_Data : callback when data received.
            *** next parameters are optional and should be changed only by an expert and an informed choice ***
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
        self._manager = manager
        self.RFP_device = RFP_device
        self._cd_handle_RFP_Data = cd_handle_RFP_Data
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
        self._state = "stopped"
        self._error = ""
        self._firmwareData = []
        self.monitorID = ""
        self._locked = ""

    log = property(lambda self: self._manager.log)
    stop = property(lambda self: self._manager._plugin.get_stop())
    isMonitored = property(lambda self: False if self.monitorID == "" else True)

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

    @property
    def domogikDevice(self):
        """Return domogik device id"""
        return self.RFP_device

    def open(self):
        """ Open serial com."""
        if self.rfPlayer is None :
            try :
                if self.fake_device != None:
                    self.log.info(u"Try to open fake RFPLAYER : %s" % self.fake_device)
                    self.rfPlayer = testserial.Serial(self.fake_device, baudrate = self.baudrate, parity = testserial.PARITY_NONE, stopbits = testserial.STOPBITS_ONE, timeout = 5)
                    self.rfPlayer.first_read = 1
                else:
                    self.rfPlayer = serial.Serial(self.RFP_device, self.baudrate, self.bytesize, self.parity,
                                                  self.stopbits, self.timeout, self.xonxoff, self.rtscts, self.dsrdtr)
                self._state = "Starting"
                self._manager.publishRFPlayerMsg(self)
                with self.RFP_Lock:
                    self.rfPlayer.reset_output_buffer()
                    self.rfPlayer.write(b'ZIA++HELLO\r')
                    id = self.rfPlayer.readline()
                print(id)
                if id.find(self.RFP_Id) != -1 :
                    self._state = "alive"
                    self._error = ""
                    self.set_JSON_Format()
                    self._cd_handle_RFP_Data(self, {'timestamp': time.time(), 'client': self, 'status': 1})
                    self.log.info(u"{0} {1} CONNECTED : {2}".format(self.RFP_type, self.RFP_device, id))
                    self._manager.publishRFPlayerMsg(self)
                    return True
                else:
                    self._error = u"{0} {1} cant't be open. Bad identification : {2}".format(self.RFP_type, self.RFP_device, id)
                    self._state = "dead"
                    self.log.error(self._error)
                    self._manager.publishRFPlayerMsg(self)
                    try:
                        self.rfPlayer.close()
                    except:
                        pass
            except :
                self.rfPlayer = None
                self._state = "dead"
                self._error = u"Error while opening {0} device {1} (disconnected ?) : {2}".format(self.RFP_type, self.RFP_device, traceback.format_exc())
                self.log.error(self._error)
                self._manager.publishRFPlayerMsg(self)
                try:
                    self.rfPlayer.close()
                except:
                    pass
        else :
            self.log.warning(u"{0} device {1} allready open".format(self.RFP_type, self.RFP_device))
        return False

    def close(self):
        """ close serial com
        """
        self.log.info(u"Close {0} on {1}".format(self.RFP_type, self.RFP_device))
        try:
            self.rfPlayer.close()
            self._state = "stopped"
        except:
            error = u"Error while closing {0} device {1} (disconnected ?) : {2}".format(self.RFP_type, self.RFP_device, traceback.format_exc())
            if self._state != 'dead': self._error = error
            self.log.error(error)
        self.rfPlayer = None
        self._cd_handle_RFP_Data(self, {'timestamp': time.time(), 'client': self, 'status': 0})
        self._manager.publishRFPlayerMsg(self)

    def start_services(self):
        """ Start all daemon service in threads"""
        listen_process = Thread(None,
                             self.listen_RFP,
                             "ListenRFP",
                             (),
                             {})
        self._manager._plugin.register_thread(listen_process)
        listen_process.start()
        write_process = Thread(None,
                             self._daemon_queue_write,
                             "write_packets_process",
                             (),
                             {})
        self._manager._plugin.register_thread(write_process)
        write_process.start()
        read_process = Thread(None,
                             self._daemon_queue_read,
                             "Read_Queue_recept",
                             (),
                             {})
        self._manager._plugin.register_thread(read_process)
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
                        if buffer is not None:
                            timestamp = time.time()
                            if buffer != "" :
                                if buffer[0] == '\r' :  # new line remove it
                                    buffer = buffer[1:]
                            if buffer != "" and len(buffer) > self.HEADSIZE:
                                if self.isMonitored : self._manager.monitorClients.rawData_report(self.monitorID, timestamp, buffer)
                                header = self.getHeaderData(buffer)
                                if header['Sync']:
                                    index = buffer.find('reqNum')
                                    if index != -1 :
                                        reqNum = self.getReqNum(buffer[self.HEADSIZE:])
                                        if reqNum != 0 : print(u"****** A ReqNum is find in data : {0}".format(reqNum))
                                    self.log.debug(u"Queuing for {0} data received : {1}".format(self.RFP_device, buffer))
                                    self.RFP_received.put_nowait({'timestamp': timestamp, 'header': header, 'data': buffer[self.HEADSIZE:]})
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
                    if buffer is not None :
                        timestamp = time.time()
                        if buffer != "" :
                            if buffer[0] == '\r' :  # new line remove it
                                buffer = buffer[1:]
                        if buffer != "" and len(buffer) > self.HEADSIZE :
                            header = self.getHeaderData(buffer)
                            if self.isMonitored : self._manager.monitorClients.rawData_report(self.monitorID, timestamp, buffer)
                            if header['Sync'] :
                                if header['Qualifier'] == self.Q_REP :
                                    if len(buffer[self.HEADSIZE:]) > 2: # some Q_REP have no data !
                                        index = buffer.find('reqNum')
                                        if index != -1 :
                                            reqNum = self.getReqNum(buffer[self.HEADSIZE:])
                                            if reqNum == ackFor['reqNum'] :
                                                self.log.debug(u"Queuing for {0} response reqNum {1} : {2}".format(self.RFP_device, reqNum, buffer))
                                                self.RFP_received.put_nowait({'timestamp': timestamp, 'header': header, 'data': buffer[self.HEADSIZE:], 'ackFor': ackFor})
                                                return True
                                        else :
                                            if ackFor['command'] == 'UPDATE FIRMWARE' : # In case no reqNum, must be end off download.
                                                self.log.debug(u"Queuing for {0} response download firmware : {1}".format(self.RFP_device, buffer))
                                                self.RFP_received.put_nowait({'timestamp': timestamp, 'header': header, 'data': buffer[self.HEADSIZE:], 'ackFor': ackFor})
                                                return True
                                        self.log.debug(u"Data response received on {0} Without reqNum, not the one we wait. Nevertheless queuing :{1}".format(self.RFP_device, buffer))
                                        self.RFP_received.put_nowait({'timestamp': timestamp, 'header': header, 'data': buffer[self.HEADSIZE:]})
                                    else :
                                        print(u" *********** No data **********")
                                else :
                                    self.log.debug(u"Data received on {0} Not reponse type the one we wait. Nevertheless queuing :{1}".format(self.RFP_device, buffer))
                                    self.RFP_received.put_nowait({'timestamp': timestamp, 'header': header, 'data': buffer[self.HEADSIZE:]})
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
            try :
                if data['header']['Qualifier'] == self.Q_REP:
                    msg = self.decode_data(data['data'])
                    if msg != {}:
                        if 'ackFor' in data :
                            if data['ackFor']['callback']is not None :
                                if data['ackFor']['command'] == 'UPDATE FIRMWARE' :
                                    data['ackFor']['callback'](msg['data'], data['ackFor'])
                                else :
                                    data['ackFor']['callback'](msg['data'], data['ackFor']['command'])
                            else :
                                msg['data'].update({'timestamp': data['timestamp']})
                                self._cd_handle_RFP_Data(self, msg)
                        else :
                            msg['data'].update({'timestamp': data['timestamp']})
                            self._cd_handle_RFP_Data(self, msg['data'])
                elif data['header']['Qualifier'] == self.Q_XML:
                    msg = self.decode_XML(data['data'])
                    if msg != {}:
                        msg.update({'timestamp': data['timestamp']})
                        self._cd_handle_RFP_Data(self, msg)
                elif data['header']['Qualifier'] == self.Q_JSON:
                    msg = self.decode_JSON(data['data'])
                    if msg != {}:
                        msg.update({'timestamp': data['timestamp']})
                        self._cd_handle_RFP_Data(self, msg)
                elif data['header']['Qualifier'] == self.Q_TXT:
                    msg = self.decode_TEXT(data['data'])
                    if msg != {}:
                        msg.update({'timestamp': data['timestamp']})
                        self._cd_handle_RFP_Data(self, msg)
            except :
                error = u"Error while reading {0} device {1}, data : {2}\n {3}".format(self.RFP_type, self.RFP_device, data, traceback.format_exc())
                self.log.warning(error)
                if self.isMonitored : self._manager.monitorClients.rawData_report(self.monitorID, time.time(), error)

        self.log.info(u"***** Receive daemon Queue {0} on {1} stopped *****".format(self.RFP_type, self.RFP_device))

    def listen_RFP(self):
        """ Start listening to RFPlayer forever.
        """
        self.log.info(u"***** Start listening {0} on {1} *****".format(self.RFP_type, self.RFP_device))
        # infinite
        while not self.stop.isSet():
                self._read_RFP_data()
        self.log.info(u"***** listening {0} on {1} stopped *****".format(self.RFP_type, self.RFP_device))
        self._cd_handle_RFP_Data(self, {'timestamp': time.time(), 'client': self, 'status': 0})

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

    def RebuildFirmware(self, data):
        """Rebuild all lines of a firmware sended by external"""
        self._locked = "updatefirmware"
        report = {'error':u"", 'rfplayerID': data['rfplayerID']}
        try :
            if data['line'] == 0 : self._firmwareData = []
            self._firmwareData.extend(data['firmwareData'].split('\n'))
            length = len(self._firmwareData)
            size = float(data['size'])
            if length >= size:
                report.update({'progress': 100, 'totalprogress': 25, 'finish': True})
                Thread(None, self.update_firmware, "UpdateFirmeware", (), {'firmwareFile':data['firmwareFile'], 'firmwareData': self._firmwareData}).start()
            else :
                report.update({'progress': int((length/size)*100), 'totalprogress': int((length/size)*25), 'finish': False})
        except :
            msg = u"Rebuild firmware on {0} device {1} fail :{2}.".format(self.RFP_type, self.RFP_device, traceback.format_exc())
            self.log.warning(msg)
            report.update({'error': msg, 'progress': 0, 'totalprogress': 0, 'finish': True})
            self._locked = ""
        return report

    def update_firmware(self, **data):
        """ Send a new firmware to RFPLAYER
            lock all request during process who take 2mins.
            @parm firmFile : firmware file location or data firmware
        """
        if type(data) == dict :
            if 'firmwareFile' in data and 'firmwareData' in data :
                fromFile = False
                firmFile = data['firmwareFile']
                offsetP = 25
                nbStep = 4
            else :
                self._locked = ""
                msg = u"Update firmware on {0} device {1} fail, bad data format :{2}.".format(self.RFP_type, self.RFP_device, data)
                self.log.warning(msg)
                self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': msg, 'progress' : 0, 'totalprogress': 0, 'msg': "", 'info': u"download"})
                return
        else :
            if os.path.isfile(data) :
                fromFile = True
                firmFile = data
                offsetP = 0
                nbStep = 3
            else :
                self._locked = ""
                msg = u"Update firmware on {0} device {1} fail : File {2} not exist.".format(self.RFP_type, self.RFP_device, data)
                self.log.warning(msg)
                self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': msg, 'progress' : 0, 'totalprogress': 0, 'msg': "", 'info': u"download"})
                return
        if self.isOpen :
            self._locked = "updatefirmware"
            try:
                with self.RFP_Lock:
                    msg = u"Start Update firmware on {0} device {1}\n  File: {2}\nWait and DO NOT SHUTDOWN the device ...".format(self.RFP_type, self.RFP_device, firmFile)
                    self.log.info(msg)
                    self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': "", 'progress' : 0, 'totalprogress': offsetP, 'msg': msg, 'info': u"download"})
                    if fromFile :
                        lines = open(firmFile,"rb").readlines()
                    else :
                        lines = data['firmwareData']
                    nbLines = len(lines)
                    n = 0
                    i = 0
                    step =[x for x in range(0,111, 10)]
                    for l in lines:
                        self.rfPlayer.write(str(l))
                        n += 1
                        progress = int(round( (n / float(nbLines)) * 100))
                        if progress == step[i]:
                            i += 1
                            msg = u"Downloading {0}%".format(progress)
                            self.log.info(msg)
                            self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': "", 'progress' : progress, 'totalprogress': offsetP+int(progress/nbStep), 'msg': msg, 'info': u"download"})
                    msg = u"Wait for internal check ...".format(self.RFP_type, self.RFP_device)
                    self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': "", 'progress' : 30, 'totalprogress': offsetP+int(100/nbStep), 'msg': msg, 'info': u"Checking"})
                    self.log.info(msg)
                    self._firmwareData = []
                    self.wait_RFP_response({'command': 'UPDATE FIRMWARE', 'reqNum': 0, 'callback': self.validate_UpdFirmware,
                                            'offsetP': offsetP+int(100/nbStep), 'nbStep': nbStep }, 80)
            except serial.SerialException:
                    self._locked = ""
                    self._firmwareData = []
                    msg = u"Error while update firmware on {0} device {1} : {2}".format(self.RFP_type, self.RFP_device, traceback.format_exc())
                    self.log.error(msg)
                    self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': msg, 'progress' : 0, 'totalprogress': 0, 'msg': ""})
                    self.close()

    def validate_UpdFirmware(self, data, ackFor =''):
        """ Check if message return after firmware update is ok, called by callback request.
            @param data: data formated in JSON
            @param ack: source request, empty if not an ack.
        """
        print("***************", data, ackFor)
        if data.find(self.RFP_FirmWare_Id) != -1 :
            offsetP = ackFor['offsetP']
            nbStep = ackFor['nbStep']
            msg = u"Internal check OK : {0}".format(data)
            self.log.info(msg)
            self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': '', 'progress' : 100, 'totalprogress': offsetP+int((100/nbStep)), 'msg': msg, 'info': u"Checking"})
            offsetP += int((100/nbStep))
            self.close()
            msg = u"Wait reboot {0}s ...".format(60)
            self.log.info(msg)
            self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': '', 'progress' : 10, 'totalprogress': offsetP+int((10/nbStep)), 'msg': msg, 'info': u"Reboot"})
            self.stop.wait(60) # wait for RFP reboot
            msg = u"Try reconnect {0}".format(self.RFP_type)
            self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': '', 'progress' : 100, 'totalprogress': offsetP+int((100/nbStep)), 'msg': msg, 'info': u"Acheived"})
            self._locked = ""
            if SerialRFPlayer.open(self) :
                self.getStatus()
                msg = u"{0} device {1} reconnected\n******* Updated successfully. *******".format(self.RFP_type, self.RFP_device)
                self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': '', 'progress' : 100, 'totalprogress': 100, 'msg': msg, 'info': u"Achieved"})
            else :
                msg = u"{0} device {1} fail to reconnect, try to restart plugin.".format(self.RFP_type, self.RFP_device)
                self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': '', 'progress' : 100, 'totalprogress': 100, 'msg': msg, 'info': u"Achieved"})
        else :
            self._locked = ""
            msg = u"Update firmware on {0} device {1} fail : {2}".format(self.RFP_type, self.RFP_device, data)
            self.log.warning(msg)
            self._manager.publishRFPlayerMsg(self, 'rfplayer.client.updatefirmware', {'error': msg, 'progress' : 0, 'totalprogress': 0, 'msg': ""})

    def getStatus(self):
        """ Send a STATUS command to rfplayer. Must be overwrited."""
        return {}

    def setStatus(self, data, ack):
        """ Set STATUS from rfplayer.  Must be overwrited.
            @param data: data formated in JSON
            @param ack: source request, empty if not an ack.
        """
        pass

    def ping(self):
        """ Send a PING command to rfplayer."""
        msg = {'timestamp': time.time(), 'client': self,  'status': 0}
        with self.RFP_Lock:
            if self.rfPlayer is not None :
                self.rfPlayer.reset_output_buffer()
                self.rfPlayer.write(b'ZIA++PING\r')
                ack = self.rfPlayer.readline()
                print(ack)
                if ack.find('PONG') != -1 :
#                    self.log.debug(u"RFPLAYER on {0} receive PING reponse".format(self.RFP_device))
                    msg['status'] = 1
                    self._error = ""
                else :
                    self._error = u"RFPLAYER on {0} don't receive PING response".format(self.RFP_device)
                    self.log.warning(self._error)
                    self._manager.publishRFPlayerMsg(self)
        self._cd_handle_RFP_Data(self, msg)

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
                try: # Due to testserial format json, single quote must be replace for fake device.
                    retval = json.loads(data.replace("'", '"'))
                except:
                    self.log.error(u"{0} on {1} fail decode JSON :{2} \n{3}".format(self.RFP_type, self.RFP_device, data, traceback.format_exc()))
#                    pass
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

    def getState(self):
        """ Return rfplayer State informations"""
        retVal= {'lasterror' : self._error}
        retVal['open'] = self.isOpen
        retVal['state'] = self._state
        retVal['error'] = self._error if self._state == "dead" else  ""
        retVal['locked'] = self._locked
        return retVal

    def getInfos(self):
        """ Return rfplayer informations"""
        retVal= self.getState()
        retVal['serialParam'] = {'baudrate' : self.baudrate, 'bytesize' : self.bytesize, 'parity' : self.parity, 'stopbits' : self.stopbits
                                 ,'timeout' : self.timeout, 'xonxoff' : self.xonxoff, 'rtscts' : self.rtscts, 'dsrdtr' : self.dsrdtr}
        retVal['status'] = {}
        return retVal


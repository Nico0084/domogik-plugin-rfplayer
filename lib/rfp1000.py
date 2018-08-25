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
import re
import traceback
from serial_rfplayer import SerialRFPlayer

CMD_SPECIF = { 'Frequency': {'cmd' : {
                                'name' :'FREQ',
                                'params' :{
                                    "H": {'values': {"0": u"Shutdown band",
                                                    "868950": u"868.950Mhz (Default)",
                                                    "868350": u"868.350Mhz"},
                                        'help': u"Set the high frequency receiver to Off."},
                                    "L": {'values': {"0": u"Shutdown band",
                                                    "433420": u"433.420Mhz",
                                                    "433920": u"433.920 Mhz (Default)"},
                                        'help': u"Set the Low frequency receiver to Off."}
                                    },
                                },
                            'help' : u"Receiver frequency on High band (around 868Mhz) or Low band (around 433Mhz). Low and high band receivers work simultaneously. \
                                Frequency Value of 0 leads to shutdown the selected receiver including the transmitter of the specified band.",
                            'type': 'band',
                            },
                'Selectivity': {'cmd' : {
                                'name' :'SELECTIVITY',
                                'params' :{
                                    "H": {'values': {"0": u"Medium selectivity (300Khz) <Default>",
                                                     "1": u"Very low selectivity (800Khz), frequency centered between used frequencies (868350-868950)",
                                                     "2": u"Very low selectivity (800Khz)",
                                                     "3": u"selectivity (500Khz)",
                                                     "4": u"Medium selectivity (300Khz)",
                                                     "5": u"High selectivity (200Khz)"},
                                        'help': u"Set the high frequency (868 Mhz) receiver selectivity."},
                                    "L": {'values': {"0": u"Medium selectivity (300Khz) <Default>",
                                                     "1": u"Very low selectivity (800Khz), frequency centered between used frequencies (433420-433920)",
                                                     "2": u"Very low selectivity (800Khz)",
                                                     "3": u"selectivity (500Khz)",
                                                     "4": u"Medium selectivity (300Khz)",
                                                     "5": u"High selectivity (200Khz)"},
                                        'help': u"Set the low frequency (433 Mhz) receiver selectivity."},
                                    },
                                },
                                'help' : u"High frequency receiver selectivity on the selected band (L:433/H:868Mhz). \
                            Selectivity is the ability to filter out of band signals.. \
                            NOTE: Higher selectivity (low value in term of Khz) means higher RF receiver sensitivity, but out of frequency transmitting appliances could be discarded. \
                            Lower selectivity (high value in term of Khz) means lower RF receiver sensitivity (lower performance). \
                            Old cheap devices can have a large frequency offset or shift over time especially when outdoor used.",
                            'type': 'band',
                            },
                'Sensitivity': {'cmd' : {
                                'name' :'SENSITIVITY',
                                'params' :{
                                    "H": {'values': {"0": u"High sensitivity (-0dB) <Default>)",
                                                     "1": u"Very low sensitivity (-18dB)",
                                                     "2": u"low sensitivity (-12dB))",
                                                     "3": u"medium sensitivity (-6dB)",
                                                     "4": u"high sensitivity (-0dB) <Default>"},
                                        'help': u"Set the high frequency (868 Mhz) receiver sensitivity."},
                                    "L": {'values': {"0": u"High sensitivity (-0dB) <Default>)",
                                                     "1": u"Very low sensitivity (-18dB)",
                                                     "2": u"low sensitivity (-12dB))",
                                                     "3": u"medium sensitivity (-6dB)",
                                                     "4": u"high sensitivity (-0dB) <Default>"},
                                        'help': u"Set the low frequency (433 Mhz) receiver sensitivity."},
                                    },
                                },
                                'help' : u"Radio Frequency receiver sensitivity on the selected band (L:433/H:868Mhz) (Ultra-High Frequency analog antenna sensitivity). \
                            Decreasing RF sensitivity could be only useful in specific cases during limited time, as pairing procedure or RF sequence learning with \
                            isolation from far RF transmitters.",
                            'type': 'band',
                            },
                'Digital Signal Processing Trigger': {'cmd' : {
                                'name' :'DSPTRIGGER',
                                'params' :{
                                    "H": {'values': {str(x):u"{0} dBm{1}".format(x, " <Default>" if x==6 else "") for x in range(4,21)},
                                        'help': u"Set the high frequency (868 Mhz) receiver DSP value in dBm."},
                                    "L": {'values': {str(x):u"{0} dBm{1}".format(x, " <Default>" if x==8 else "") for x in range(4,21)},
                                        'help': u"Set the low frequency (433 Mhz) receiver DSP value in dBm."},
                                    },
                                },
                                'help' : u"Digital Signal Processing trigger on the selected band (L:433/H:868Mhz) \
                            Define the smallest signal amplitude leading to start frame detection and analysis. \
                            Low trigger value means high sensitivity. \
                            Too big trigger value leads to forget useful frames. \
                            Too low trigger value leads to detect ghostly frames, generated by floor noise, and sometimes forget useful frames during this time.",
                            'type': 'band',
                            },
                'RFlink Trigger': {'cmd' : {
                                'name' :'RFLINKTRIGGER',
                                'params' :{
                                    "H": {'values': {str(x):u"{0} dBm{1}".format(x, " <Default>" if x==6 else "") for x in range(4,21)},
                                        'help': u"Set the high frequency (868 Mhz) receiver smallest signal amplitude value in dBm."},
                                    "L": {'values': {str(x):u"{0} dBm{1}".format(x, " <Default>" if x==8 else "") for x in range(4,21)},
                                        'help': u"Set the low frequency (433 Mhz) receiver smallest signal amplitude value in dBm."},
                                    },
                                },
                                'help' : u"RFLINK trigger on the selected band (L:433/H:868Mhz). \
                            Define the smallest signal amplitude leading to start frame detection and analysis. \
                            Low trigger value means high sensitivity. \
                            Too big trigger value leads to forget useful frames. \
                            Too low trigger value leads to detect ghostly frames, generated by floor noise, and sometimes forget useful frames during this time.",
                            'type': 'band',
                            },
                'Listen Before Talk': {'cmd' : {
                                'name' :'LBT',
                                'type' :'select',
                                'params' : {
                                        'values': dict({"0": u"Inhibits LBT function"}.items() +
                                                {str(x):u"{0} dBm{1}".format(x, " <Default>" if x==16 else "") for x in range(6,31)}.items()),
                                        'help': u"Set receiver Listen Before Talk value in dBm."},
                                },
                            'help' : u"Out of bounds value of val leads to come back to the default value. \
                            Val = 0 inhibits LBT function. \
                            Default is LBT enabled (very highly recommended). \
                            When enabled, the transmitter will “listen” the current activity on the same frequency and wait a silence before to “talk”. \
                            Sent frames cannot be delayed more than 3 seconds.",
                            'type': 'system'
                        },
                'Set MAC':{'cmd' : {
                                'name' :'SETMAC',
                                'type' :'string',
                                'params' : {
                                        'values': "^0x([0-9A-F]{2}){4}$|^[1-9]$|^[0-9]{2,9}$",
                                        'help': u"MAC address unsigned 32 bits value. eg : 123456765 or 0x2AB265C3 format."},
                                },
                                'help' : u"Warning! Changing the MAC address is without effect on incoming RF Frames. \
But changing the MAC address will modify the ID contained in outcoming RF Frames on most protocols. Pairing between the dongle and actuators could be broken. \
Each Dongle owns a different MAC address configured at the factory.",
                                'type': 'system',
                            },
                'Factory reset':{'cmd' : {
                                'name' :'FACTORYRESET',
                                'type' :'select',
                                'params' : {
                                        'values': {"": u"Preserve PARROT records and TRANSCODER configuration.",
                                                   "ALL": u"Erases all, including PARROT records and TRANSCODER configuration."},
                                        'help': u"Select reset mode."},
                                },
                                'help' : u"Restore factory default parameters.",
                                'type': 'system',
                            },
                'LED activity':{'cmd' : {
                                'name' :'LEDACTIVITY',
                                'type' :'select',
                                'params' : {
                                        'values': {"0": u"Disable",
                                                   "1": u"Enable"},
                                        'help': u"Select LED activity mode."},
                                },
                                'help' : u"Enable ou disable LED activity related to RF flow. \
Default is 1 after factory RESET. LED activity cannot be disabled during PARROTLEARN and TRANSCODER processings or when the dongle signals an error.",
                                'type': 'system',
                            },
                'Init Leaky Buckets':{'cmd' : {
                                'name' :'INITLB',
                                'type' :'empty',
                                'params' : {
                                        'values': "",
                                        'help': u"Initialization of the leaky buckets (LB) to full level"},
                                },
                                'help' : u"Each frequency owns a leaky bucket. At each frame sent, the leaky bucket level decreases, \
but idle time increases this level. Frames are not send and discarded when LB level reaches 0. \
The LB defines a maximum duty cycle per hour defined by European laws (e.g. 433Mhz: 10%, 868.350Mhz: 1%, 868.950Mhz: 0.1%) \
where the channel is usable to send frames. INTLB could be useful during tests to disable LB limitation of bandwidth.",
                                'type': 'system',
                            },
                'Jamming detection threshold':{'cmd' : {
                                'name' :'JAMMING',
                                'type' :'select',
                                'params' : {
                                        'values': {"0": u"Disable detection.",
                                                   "1": u"1 - Extremely sensitive but should lead to “false positives” events.",
                                                   "2": u"2 - Very sensitive, disturbances on single frequency is enough.",
                                                   "3": u"3 - Very sensitive, disturbances on single frequency is enough.",
                                                   "4": u"4 - Sensitive, disturbances on single frequency is enough.",
                                                   "5": u"5 - Less sensitive, disturbances on single frequency is enough.",
                                                   "6": u"6 - Sensitive, disturbances on both frequencies",
                                                   "7": u"7 - Recommended, disturbances on both frequencies",
                                                   "8": u"8 - Less sensitive disturbances on both frequencies.",
                                                   "9": u"9 - At least one of the frequencies must be on maximum disturbances.",
                                                   "10": u"10 - Both frequencies must be on maximum disturbances, limits “false positives” events.",
                                                   },
                                        'help': u"Select jamming sensitivity."},
                                },
                                'help' : u"The JAM’ALERT function detects jamming attempts of your installation on all protocols operating on the 433 and 868 Mhz frequency bands. \
Level 0 cancels the detection. A level of 1 is extremely sensitive but will probably cause alerts called «false positives». \
A level of 10 is much less sensitive of course, but is almost guaranteed not to cause false positives. \
Note each frequency receives a score between 0 and 5. Then, the 2 notes are added. \
A threshold above 5 requires simultaneous jamming on the 433Mhz and 868Mhz. \
We recommend a value between 7 and 10.",
                                'type': 'system',
                            },
                'Jamming simulation':{'cmd' : {
                                'name' :'JAMMING SIMULATE',
                                'type' :'empty',
                                'params' : {
                                        'values': "",
                                        'help': u"Will force receiving “JAMMING ON” frame. “JAMMING OFF” Frame is received 5 seconds later."},
                                },
                                'help' : u"Simulator command to send yourself alerts to virtually test the presence of a jammer.",
                                'type': 'system',
                            },
                'Capture':{'Entry' : {
                                'code' :'"ENTRY {0}".format(value)',
                                'type' :'select',
                                'params' : {
                                        'values': {str(x):u"{0}".format(x) for x in range(0,31)},
                                        'help': u"Record number (0 to 31)"},
                                },
                            'Comment' : {
                                'code' :'"[{0}]".format(value)',
                                'type' :'string',
                                'params' : {
                                        'values': "",
                                        'help': u"User reminder"},
                                },
                            'Source' : {
                                'code' :'"{0}".format(value)',
                                'type' :'select',
                                'params' : {
                                        'values': {"X10": u"X10",
                                                   "VISONIC": u"VISONIC",
                                                   "BLYSS": u"BLYSS",
                                                   "CHACON": u"CHACON",
                                                   "OREGON": u"OREGON",
                                                   "DOMIA": u"DOMIA",
                                                   "OWL": u"OWL",
                                                   "X2D": u"X2D",
                                                   "RFY": u"RFY",
                                                   "KD101": u"KD101",
                                                   "PARROT": u"PARROT"},
                                        'help': u"Source protocol"},
                                },
                            'ID source' : {
                                'code' :'"ID {0}".format(value)',
                                'type' :'string',
                                'params' : {
                                        'values': "",
                                        'help': u"User reminder"},
                                },
                            'help' : u"Select record number to set.",
                            'type': 'transcoder',
                            },
            }

class SerialRFP1000(SerialRFPlayer):
    """Base class to handle RFPLAYER on serial port"""

    def __init__(self, manager, rfp_device, cd_handle_RFP_Data,
                 baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE, timeout=0.1, xonxoff=0, rtscts=1, dsrdtr=None, fake_device=None):
        """ Init An RFP1000 device and start communication.
            @param manager : RFPManager instance
            @param rfp_device : rfplayer device (ex : /dev/rfplayer)
            @param cd_handle_RFP_Data : callback when data received.
            *** next parameters are optional and should be changed only by an expert and an informed choice ***
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
        self._sendMessage = cd_handle_RFP_Data
        self.status = {}
        self.transcodeData = {}
        SerialRFPlayer.__init__(self, manager, rfp_device, self.handle_msg,
                                baudrate, bytesize, parity, stopbits, timeout, xonxoff, rtscts, dsrdtr, fake_device)

    @property
    def RFP_Id(self):
        """ Get value returned by HELLO command"""
        return "ZIA--Welcome to Ziblue Dongle "

    def open(self):
        """ Open serial com and start communication."""
        if SerialRFPlayer.open(self) :
            self.start_services()
            self.getStatus()
            self.getTrancodeData()
            return True
        else :
            return False

    def getStatus(self):
        """ Send a STATUS command to rfplayer"""
        if  self.rfPlayer is not None :
            self.log.info(u"Get Status of {0}".format(self.RFP_device))
            self.send_to_RFP('STATUS JSON', True, self.setStatus)

    def setStatus(self, data, ack=''):
        """ Decode Status data from RFP100 JSON, can be call by callback request.
            @param data: data formated in JSON
            @param ack: source request, empty if not an ack.
        """
        if ack == 'STATUS JSON' :
            self.status = {}
            self.log.debug(u"RFP1000 on {0} receive STATUS result".format(self.RFP_device))
        else:
            self.log.debug(u"RFP1000 on {0} receive complement STATUS".format(self.RFP_device))
        if 'systemStatus' in data :
            self.status['systemStatus'] = data['systemStatus']
        if 'radioStatus' in data :
            self.status['radioStatus'] = data['radioStatus']
        self._manager.publishRFPlayerMsg(self)

    def getTrancodeData(self):
        """ Send a transcode retrieve data command to rfplayer"""
        if  self.rfPlayer is not None :
            self.log.info(u"Get transcode data of {0}".format(self.RFP_device))
            self.send_to_RFP('STATUS TRANSCODER JSON', True, self.setTranscodeData)

    def setTranscodeData(self, data, ack=''):
        """ Decode trancode data from RFP100 JSON, can be call by callback request.
            @param data: data formated in JSON
            @param ack: source request, empty if not an ack.
        """
        self.log.debug(u"RFP1000 on {0} receive Transcoder result".format(self.RFP_device))
        if 'transcoderStatus' in data :
            value = {}
            entry = 'unknown'
            for param in data['transcoderStatus']['info'] :
                if param['n'] == 'entry' :
                    entry = param['v']
                else :
                    value[param['n']] = {'value': param['v']}
                    if 'c' in param :
                        value[param['n']]['comment'] = param['c']
                self.transcodeData[entry] = value
            self._manager.publishRFPlayerMsg(self)

    def handle_msg(self, client, msg):
        """Handle msg to MQ"""
        print(msg)
        if "radioStatus" in msg :
            self.setStatus(msg)
            return
        if "systemStatus" in msg :
            self.setStatus(msg)
            return
        if "transcoderStatus" in msg :
             self.setTranscodeData(msg)
             return
        self.log.debug("Sending to 0MQ : {0}".format(msg))
        self._sendMessage(client, msg)

    def getInfos(self):
        """Return All informations formated to UI"""
        retval = SerialRFPlayer.getInfos(self)
        retval['status'] = self.formatStatus()
        retval['cmdsystem'] = self.getCommansSystem()
        retval['transcoder'] = self.transcodeData
        return retval

    def getProtocolsList(self, protocol,  status='enabled'):
        """Return list of protocol in specific status (enabled or available)"""
        if self.isOpen :
            for i, param in enumerate(self.status['systemStatus']['info']):
                k = param.keys()[0]
                if k == protocol and status in self.status['systemStatus']['info'][i][protocol]:
                    return self.status['systemStatus']['info'][i][protocol][status]['p']
            return []

    def formatStatus(self):
        retVal = {}
        if 'radioStatus' in self.status :
            retVal['radioStatus'] = []
            for i, bands in self.status['radioStatus'].iteritems() :
                for band in bands :
                    if 'i' in band :
                        b = {'band':'unknown', 'params':{}}
                        typeP = 'values'
                        for param in band['i']:
                            if param['n'] == 'Frequency' :
                                if param['v'].find('433') != -1 :
                                    b['band'] = "433Mhz"
                                    typeP = 'L'
                                else:
                                    b['band'] = "868Mhz"
                                    typeP = 'H'
                                break
                        for param in band['i']:
                            detail = dict()
                            detail['value'] = param['v']
                            detail['unit'] = param['unit']
                            detail['comment'] = param['c']
                            detail['help'] = ""
                            if param['n'] in CMD_SPECIF :
                                detail['help'] = CMD_SPECIF[param['n']]['help']
                                for cType in CMD_SPECIF[param['n']]['cmd']['params'] :
                                    if cType == typeP :
                                        if typeP == 'values' :
                                            detail['command'] = CMD_SPECIF[param['n']]['cmd']['params']
                                        else :
                                            detail['command'] = CMD_SPECIF[param['n']]['cmd']['params'][typeP]
                                        break
                            b['params'].update({param['n']:detail})
                        retVal['radioStatus'].append(b)
        else :
            retVal['radioStatus'] = 'Not read'
        if 'systemStatus' in self.status :
            prot = dict()
            detail = dict()
            for param in self.status['systemStatus']['info'] :
                if 'transmitter' not in param and 'receiver' not in param and 'repeater' not in param :
                    detail[param['n']] = {'value': param['v'], 'unit': param['unit'], 'comment': param['c']}
                else :
                    key = param.keys()[0]
                    if key not in prot : prot[key] = {}
                    if 'available' in param[key] :
                        for p in param[key]['available']['p'] :
                            if p not in prot[key] : prot[key][p] = False
                    elif 'enabled' in param[key] :
                        for p in param[key]['enabled']['p'] :
                            prot[key][p] = True

            retVal['systemStatus'] = {'infos': detail, 'protocols': prot}
        else :
            retVal['systemStatus'] = 'Not read'
        return retVal

    def getCommansSystem(self):
        """Return list of special dongle commands"""
        retval = {}
        for cmd in CMD_SPECIF:
            if CMD_SPECIF[cmd]['type'] == 'system' :
                retval[cmd]= CMD_SPECIF[cmd]
        return retval

    def setProtocol(self, protocol, mode, state) :
        """disable/unable protocol for mode"""
        if self.isOpen :
            st = False
            mode = mode.upper()
            error = u"Bad protocol activation format({0},{1},{2})".format(mode, protocol, state)
            self.log.debug(u"Protocol activation {0} {1} {2}".format(mode, protocol, state))
            status = self.formatStatus()
            if mode == 'RECEIVER' :
                if protocol in status['systemStatus']['protocols']['receiver'].keys() :
                    st = "+" if state == 'true' else "-"
                    error = ""
            elif mode == 'REPEATER' :
                if protocol in status['systemStatus']['protocols']['receiver'].keys() :
                    st = "+" if state == 'true' else "-"
                    error = ""
            elif mode == 'TRANSMITTER' :
                if protocol in status['systemStatus']['protocols']['receiver'].keys() :
                    st = "+" if state == 'true' else "-"
                    error = ""
            if st : self.send_to_RFP('{0} {1} {2}'.format(mode, st, protocol), True, self.protocolEnabledReceived)
        else :
            error = u"Dongle RFP1000 not open on serial : {0}".format(self.RFP_device)
        return {'error': error}

    def protocolEnabledReceived(self, data, ack=''):
        """Received protocols enable info in text format"""
        data = data.rstrip().split(" ")
        protocol = ""
        if data[0] == 'RECEIVED' : protocol = 'receiver'
        elif data[0] == 'TRANSMITTED' : protocol = 'transmitter' # TODO must be checked for other protocol !!!!
        elif data[0] == 'REPEATED' : protocol = 'repeater' # TODO must be checked for other protocol !!!!
        if protocol in ['receiver', 'transmitter', 'repeater'] and data[1] == 'PROTOCOLS:' :
            item = -1
            for i, param in enumerate(self.status['systemStatus']['info']):
                k = param.keys()[0]
                if k == protocol and 'enabled' in self.status['systemStatus']['info'][i][protocol]:
                    print("***** Existing enable ****")
                    item = i
                    break
            if item == -1 :
                print("---- no Existing enable ----")
                self.status['systemStatus']['info'].append({protocol:{u'enabled': {u'p': data[2:]}}})
                item = len(self.status['systemStatus']['info']) -1
            else :
                self.status['systemStatus']['info'][item][protocol][u'enabled'] = {u'p': data[2:]}
            self.log.info(u"{0} activate {1} protocols {2}".format(self.RFP_device, protocol, self.status['systemStatus']['info'][item][protocol][u'enabled']['p']))
            self._manager.publishRFPlayerMsg(self)
            return
        self.log.warning(u"{0} activate protocols recieved in bad format {1}".format(self.RFP_device, data))

    def setBandParameter(self, band, command, value):
        """Set a band command parameter"""
        if self.isOpen :
            error = u"Bad band parameter format({0},{1},{2})".format(band, command, value)
            self.log.debug(u"Band parameter setting {0} {1} {2}".format(band, command, value))
            if '433' in band : band = "L"
            elif '868'in band : band = "H"
            if band in ["L", "H"] :
                if command in CMD_SPECIF :
                    if 'cmd' in CMD_SPECIF[command]:
                        if band in CMD_SPECIF[command]['cmd']['commands'].keys():
                            if value in CMD_SPECIF[command]['cmd']['commands'][band]['values'].keys():
                                cmdline = "{0} {1} {2}".format(CMD_SPECIF[command]['cmd']['name'], band, value)
                                self.sendCmdLine(cmdline)
                                self.getStatus()
                                error = ""
                            else :
                                error = u"{0} band parameter {1} bad value : {2}, availaible : {3}".format(band, command, value, CMD_SPECIF[command]['cmd']['commands'][band]['values'].keys())
                        else :
                            error = u"parameter {0} don't exist for band {1}, availaible : {2}".format(command, band, CMD_SPECIF[command]['cmd']['commands'].keys())
                    else :
                        error = u"{0} band parameter {1} is on read only".format(band, command)
        else :
            error = u"Dongle RFP1000 not open on serial : {0}".format(self.RFP_device)
        return {'error': error}

    def sendCommandSystem(self, cmd, value):
        """Set a band parameter"""
        if self.isOpen :
            error = u"Bad command system format({0},{1})".format(cmd, value)
            self.log.debug(u"Handle command system {0} {1}".format(cmd, value))
            for command in CMD_SPECIF :
                if 'cmd' in CMD_SPECIF[command] and CMD_SPECIF[command]['type'] == 'system':
                    if cmd == CMD_SPECIF[command]['cmd']['name'] :
                        cmdline = ""
                        if CMD_SPECIF[command]['cmd']['type'] == 'select' :
                            if value in CMD_SPECIF[command]['cmd']['params']['values'].keys():
                                cmdline = "{0} {1}".format(CMD_SPECIF[command]['cmd']['name'], value)
                            else :
                                error = u"Command system {0} bad value : {1}, availaible : {2}".format(cmd, value, CMD_SPECIF[command]['cmd']['params']['values'].keys())
                        elif CMD_SPECIF[command]['cmd']['type'] == 'string' :
                            if re.match(r'{0}'.format(CMD_SPECIF[command]['cmd']['params']['values']), value) is not None :
                                cmdline = "{0} {1}".format(CMD_SPECIF[command]['cmd']['name'], value)
                            else :
                                error = "Command system {0}, value ({1}) doesn't match regular expression : {2}".format(cmd, value, CMD_SPECIF[command]['cmd']['params']['values'])
                        elif CMD_SPECIF[command]['cmd']['type'] == 'empty' :
                            cmdline = "{0}".format(CMD_SPECIF[command]['cmd']['name'])
                        else :
                            error = u"Command system {0} value : {1} has no type : {2}".format(cmd, value, CMD_SPECIF[command]['cmd'])
                        if cmdline != "" :
                                self.sendCmdLine(cmdline)
                                self.getStatus()
                                error = u""
                                break
                    else :
                        error = u"Command system {0} doesn't exist.".format(cmd)
        else :
            error = u"Dongle RFP1000 not open on serial : {0}".format(self.RFP_device)
        return {'error': error}

    def setTranscoderEntry(self, data):
        """Set transcoder entry"""
        if self.isOpen :
            error = u"Bad transcoder entry format({0})".format(data)
            self.log.debug(u"Handle transcoder entry format {0}".format(data))
            try :
                if data['entry'] != "" :
                    command = "TRANSCODER ENTRY {0}".format(data['entry'])
                    if data['mode'] == 'MANUAL' or data['mode'] == '':
                        command = '{0} {1} {2}'.format(command, data['srcProtocols'], data['srcAddr'])
                        if data['srcSubtype'] != "" : command = '{0} SUBTYPE {1}'.format(command, data['srcSubtype'])
                        if data['srcQualifier'] != "" : command = '{0} QUALIFIER {1}'.format(command, data['srcQualifier'])
                    elif data['mode'] == 'CAPTURE' :
                        command = '{0} {1} CAPTURE'.format(command, data['srcProtocols'])
                    elif data['mode'] == 'KEEP' :
                        command = '{0} KEEP'.format(command)
                    else :
                        return {'error': u"Bad transcoder set mode {0}".format(data)}
                    command = '{0} TO {1} {2} {3}'.format(command, data['outCmd'], data['outProtocols'], data['outAddr'])
                    if data['outCmd'] == 'DIM' :
                        command = '{0} %{1}'.format(command, int(data['outDim']))
                    if data['outQualifier'] != "" : command = '{0} QUALIFIER {1}'.format(command, data['outQualifier'])
                    if data['outBrust'] != "" : command = '{0} BURST {1}'.format(command, data['outBrust'])
                    if data['comment'] != "" : command = '{0} [{1}]'.format(command, data['comment'])
                    if command != "" :
                            self.sendCmdLine(command)
                            self.getTrancodeData()
                            error = u""
            except :
                self.log.warning(error)
        else :
            error = u"Dongle RFP1000 not open on serial : {0}".format(self.RFP_device)
        return {'error': error}

    def sendAction(self, cmdAction):
        """Send an ASCII command action to RFPlayer"""
        if self.isOpen :
            protocols = self.getProtocolsList('transmitter', 'available')
            if protocols != []:
                if 'protocol'in cmdAction and 'action' in cmdAction and 'address' in cmdAction :
                    print(protocols)
                    if cmdAction['protocol'] in protocols:
                        dimVal= ""
                        if cmdAction['action'] == 'DIM':
                            if 'dim' in cmdAction :
                                try :
                                    dimVal = int(cmdAction['dim'])
                                    if dimVal >= 0 and dimVal <= 100 :
                                        dimVal = " %{0}".format(dimVal)
                                    else : dimVal = ""
                                except :
                                    pass
                                if dimVal == "" :
                                    return {"error": u"Bad DIM action format, dim value ({0}) not a valide number (0 to 100)." .format(cmdAction['dim'])}
                            else :
                                return {"error": u"Bad DIM action format, missing dim value."}
                        if  cmdAction['action'] != '':
#                            cmd = "{0} ID {1} {2}{3}".format(cmdAction['action'], cmdAction['address'], cmdAction['protocol'],  dimVal)
                            cmd = "{0} {1} {2}{3}".format(cmdAction['action'], cmdAction['address'], cmdAction['protocol'],  dimVal)
                        if cmdAction['burst'] != '': cmd += " BURST {0}".format(cmdAction['burst'])
                        if cmdAction['qualifier'] != '': cmd += " QUALIFIER {0}".format(cmdAction['qualifier'])
                        self.sendCmdLine(cmd)
                    else :
                        return {"error": u"Bad action protocols : {0}.".format(cmdAction['protocol'])}
                else :
                    return {"error": u"Bad action format : {0}".format(cmdAction)}
            else :
                return {"error": u"Dongle RFP1000 have no available action protocols."}

#            {'protocol': protocol, 'action': action,'address': address, 'burst': burst, 'qualifier': qualifier, 'dim': dim},
        else :
            return {"error": u"Dongle RFP1000 not open on serial : {0}".format(self.RFP_device)}
        return {"error": u""}

    def processRequest(self, request, data):
        """Callback come from MQ (request with reply)
            Allready filtered by 'rfplayer.client' """
        report = SerialRFPlayer.processRequest(self, request, data)
        if "don't handle request" in report['error']:
            report = {'error' : u"Serial rfp1000 don't handle request {0}, data : {1}".format(request, data)}
        if request == 'cmdsystem' :
            report = self.sendCommandSystem(data['cmd'], data['value'])
        elif request == 'settranscoder' :
            report = self.setTranscoderEntry(data)
        return report

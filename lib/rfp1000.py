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

BAND_SPECIF = { 'Frequency': {'cmd' : {
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
                            Frequency Value of 0 leads to shutdown the selected receiver including the transmitter of the specified band."
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
                            Old cheap devices can have a large frequency offset or shift over time especially when outdoor used."
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
                            isolation from far RF transmitters."
                            },
                'DspTrigger': {'cmd' : {
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
                            Too low trigger value leads to detect ghostly frames, generated by floor noise, and sometimes forget useful frames during this time."
                            },
                'RFlinkTrigger': {'cmd' : {
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
                            Too low trigger value leads to detect ghostly frames, generated by floor noise, and sometimes forget useful frames during this time."
                            },
                'LBT':        {'cmd' : {
                                'name' :'LBT',
                                'params' : {
                                        'values': dict({"0": u"Inhibits LBT function"}.items() +
                                                {str(x):u"{0} dBm{1}".format(x, " <Default>" if x==16 else "") for x in range(6,31)}.items()),
                                        'help': u"Set receiver Listen Before Talk value in dBm."},
                                },
                                'help' : u"Out of bounds value of val leads to come back to the default value. \
                            Val = 0 inhibits LBT function. \
                            Default is LBT enabled (very highly recommended). \
                            When enabled, the transmitter will “listen” the current activity on the same frequency and wait a silence before to “talk”. \
                            Sent frames cannot be delayed more than 3 seconds."
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

    def handle_msg(self, client, msg):
        """Handle msg to MQ"""
        print(msg)
        if "radioStatus" in msg :
            self.setStatus(msg)
            return
        if "systemStatus" in msg :
            self.setStatus(msg)
            return
        self.log.debug("Sending to 0MQ : {0}".format(msg))
        self._sendMessage(client, msg)

    def getInfos(self):
        """Return All informations formated to UI"""
        retval = SerialRFPlayer.getInfos(self)
        retval['status'] = self.formatStatus()
        return retval

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
                            if param['n'] in BAND_SPECIF :
                                detail['help'] = BAND_SPECIF[param['n']]['help']
                                for cType in BAND_SPECIF[param['n']]['cmd']['params'] :
                                    if cType == typeP :
                                        if typeP == 'values' :
                                            detail['command'] = BAND_SPECIF[param['n']]['cmd']['params']
                                        else :
                                            detail['command'] = BAND_SPECIF[param['n']]['cmd']['params'][typeP]
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

            retVal['systemStatus'] = {'infos': detail, 'protocoles': prot}
        else :
            retVal['systemStatus'] = 'Not read'
        return retVal

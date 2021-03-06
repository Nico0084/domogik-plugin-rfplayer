# !/usr/bin/python
#-*- coding: utf-8 -*-

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

import traceback
import threading
import time

from domogik_packages.plugin_rfplayer.lib.infotypes import *
from domogik_packages.plugin_rfplayer.lib.defs import *
from domogik_packages.plugin_rfplayer.lib.monitor_rfplayer import ManageMonitorClient
from domogik_packages.plugin_rfplayer.lib.rfp1000 import SerialRFP1000

def checkIfConfigured(deviceType,  device):
    """ Check if device_type have his all paramerter configured.
        Methode must be update for all existing RFPLayer device_type in json
    """
    if deviceType in RFP_CLIENTS_DEVICES :
        if device["parameters"]["device"]["value"] !="" : return True
        else : return False
    return False

class RFPManager(object):

    """" Manager RFPlayer(s)
    """
    def __init__ (self, plugin, cb_send_sensor) :
        """Init RFPlayer manager client"""
        self._plugin = plugin
        self._send_sensor = cb_send_sensor
        self._stop = plugin.get_stop()  # TODO : pas forcement util ?
        self.rfpClients = {} # list of all RFPlayer
        self.monitorClients = ManageMonitorClient(self)
        self.monitorClients.start()  # Start supervising nodes activity to helper log.
        self._plugin.publishMsg('rfplayer.manager.state', self.getManagerInfo())
        # get the devices list
        self.refreshDevices(self._plugin.get_device_list(quit_if_no_device = False, max_attempt = 2))
        if not self.rfpClients :
            self.log.warning(u"No device RFPlayer created in domogik. Create one with admin device creation.")
        self.log.info(u"Manager RFPlayer Clients is ready.")

    @property
    def log(self):
        return self._plugin.log

    @property
    def stop(self):
        return self._plugin.get_stop()

    def _del__(self):
        """Delete all RFPLayer CLients"""
        print u"try __del__ rfpClients"
        self.monitorNodes.stop()
        for id in self.rfpClients : self.rfpClients[id] = None

    def closeClients(self):
        """Close all RFPLayer CLients"""
        self.log.info(u"Closing RFPManager.")
        for id in self.rfpClients : self.rfpClients[id].close()

    def sendRFPcmd(self, device, cmd_id, values):
        """Send command to RFPlayer"""
        print(cmd_id, values)
        cmd = None
        for k in device['commands'].keys():
            if  device['commands'][k]['id'] == cmd_id:
                cmd = device['commands'][k]
                break
        if cmd is not None :
            if 'dongle_id' in device['parameters'] :
                CliName = device['parameters']['dongle_id']['value']
                client = self.getClientFromDevName(CliName)
                if client is not None :
                    iType = getInfoTypeFromCmd(device, k, cmd, values)
                    if iType is not None :
                        #Add device address
                        client.send_to_RFP(iType.get_cmd_to_RFP_data(k, cmd, values))
                        return True, None
                    return False, u"Command {0} for {1} does not match to an infoType.".format(cmd, device['device_type_id'])
                return False, u"Command {0} don't find rfplayer dongle named {1}.".format(cmd, CliName)
            return False, u"Command {0} device {1} have no dongle id.".format(cmd, device['name'])
        else :
            self.log.warning(u"Command id {0} not exist in device {1}".format(cmd_id, device))
            return False, u"Command id {0} not exist in device {1}".format(cmd_id, device['name'])

    def addClient(self, dmgDevice):
        """Add a RFPLayer from domogik device"""
        if dmgDevice["device_type_id"] in RFP_CLIENTS_DEVICES:
            clID = getRFPId(dmgDevice)
            if self.rfpClients.has_key(clID) :
                self.log.debug(u"Manager RFPLayer : RFPLayer Client {0} already exist, not added.".format(clID))
                return False
            else:
                if checkIfConfigured(dmgDevice["device_type_id"], dmgDevice ) :
                    if dmgDevice["device_type_id"] == "rfplayer.rfp1000" :
                        self.rfpClients[clID] = SerialRFP1000(self, self._plugin.get_parameter(dmgDevice, 'device'), self._handle_RFP_Data,
                                                              fake_device = self._plugin.options.test_option)
                    else :
                        self.log.error(u"Manager RFPLayer : RFPLayer Client type {0} not exist, not added.".format(clID))
                        return False
                    self.log.info(u"Manager RFPLayer : created new client {0}.".format(clID))
                    if self.rfpClients[clID].open() :
                        # Start thread for starting rfplayer services
                        timer = self._plugin.get_parameter(dmgDevice, 'timer_status')
                        if timer != 0 :
                            Timer(timer, self.rfpClients[clID].ping, self._plugin).start()
                        else :
                            self.log.info(u"Ping timer for client {0} disable.".format(clID))
                else :
                    self.log.warning(u"Manager RFPLayer : device not configured can't add new client {0}.".format(clID))
                    return False
            return True
        else : return False

    def removeClient(self, clID):
        """Remove a RFPLayer client and close it"""
        client = self.getClient(clID)
        if client :
            client.close()
            self.rfpClients.pop(clID)

    def getClient(self, clID):
        """Get RFPLayer client object by id."""
        if self.rfpClients.has_key(clID) :
            return self.rfpClients[clID]
        else :
            return None

    def getClientFromDevName(self, name):
        """Get RFPLayer client object by id."""
        for clID in self.rfpClients.keys():
            if clID.split(".")[0] == name:
                return self.rfpClients[clID]
        return None

    def getIdsClient(self, idToCheck):
        """Get RFPLayer client key ids."""
        retval = []
        findId = ""
        self.log.debug (u"getIdsClient check for device : {0}".format(idToCheck))
        if isinstance(idToCheck, SerialRFP1000) :
            for clID in self.rfpClients.keys() :
                if self.rfpClients[clID] == idToCheck :
                    retval = [clID]
                    break
        else :
            self.log.debug (u"getIdsClient, no RFPClient instance...")
            if isinstance(idToCheck,  str) :
                findId = idToCheck
                self.log.debug (u"str instance...")
            else :
                if isinstance(idToCheck,  dict) :
                    if idToCheck.has_key('device') : findId = idToCheck['device']
                    else :
                        if idToCheck.has_key('name') and idToCheck.has_key('id'):
                            findId = getRFPId(idToCheck)
            if self.rfpClients.has_key(findId) :
                retval = [findId]
                self.log.debug (u"key id type find")
            else :
                self.log.debug (u"No key id type, search {0} in client {1}".format(findId, self.rfpClients.keys()))
                for id in self.rfpClients.keys() :
                    self.log.debug(u"Search in list by device key : {0}".format(self.rfpClients[id].domogikDevice))
                    if self.rfpClients[id].domogikDevice == findId :
                        self.log.debug('find RFPLayer Client :)')
                        retval.append(id)
        self.log.debug(u"getIdsClient result : {0}".format(retval))
        return retval

    def checkClientsRegistered(self, dmgDevices):
        """Check if RFPLayer clients existing or not in domogiks devices and do creation, update or remove action."""
        for device in dmgDevices:
            if device["device_type_id"] in RFP_CLIENTS_DEVICES:
                cId = getRFPId(device)
                if self.rfpClients.has_key(cId) :  # Client exist with same ref, just do an update of parameters
                     self.rfpClients[cId].updateDevice(device)
                else :
                    exist_Id = self.getIdsClient(device)
                    if exist_Id != [] :
                        if len(exist_Id) == 1 : # Client exist but without same ref, just do an update of parameters
                            self.rfpClients[cId] = self.rfpClients.pop(exist_Id[0]) # rename and change key client id
                            self.Plugin.log.info(u"RFPlayer client {0} renamed {1}".format(exist_Id[0], cId))
                            self.rfpClients[cId].updateDevice(device)  # update client
                        else :
                            self.log.warning(u"Inconsistency clients for same domogik device. Clients: {0}, domogik device :{1}".format(exist_Id, device))
                    else :  # client doesn't exist, create it:
                        try :
                            if self.addClient(device) :
                                self.log.info(u"Ready to work with device {0}".format(cId))
                        except:
                            self.log.error(traceback.format_exc())
        # check clients to remove
        delC = []
        for cId in self.rfpClients:
            for device in dmgDevices:
                if getRFPId(device) == cId :
                    find = True
                    break;
            if not find : delC.append(cId)
        for cId in delC : self.removeClient(cId)

    def refreshDevices(self, dmgDevices):
        """ Call all clients to refreshe they devices"""
        self.checkClientsRegistered(dmgDevices)
        self._plugin.publishMsg('rfplayer.manager.state', self.getManagerInfo())

    def getCliDmgDevices(self, id, dmgDevices):
        """ Return domogik device of client."""
        for cId in self.rfpClients:
            for device in dmgDevices:
                if getRFPId(device) == id:
                    return device
        return None

    def liklyDmgDevices(self, iType):
        """ Return possible DmgDevices from infoType build with RFP data"""
        likelyDevices = {iType.dmgDevice_Id : {'listSensors':  iType.get_Available_Sensors(),
                               'listCmds': iType.get_Available_Commands(),
                               'reference': u"Protocol {0}".format(iType.protocol_name)}}
        print(u"***************** likly domogik devices for sensor ****************")
        print(likelyDevices)
        knownDeviceTypes = self.findDeviceTypes(likelyDevices)
        print(u"***************** existing domogik device_types for sensor ****************")
        print(knownDeviceTypes)
        if knownDeviceTypes :
            self.registerDetectedDevice(knownDeviceTypes)

    def findDeviceTypes(self, likelyDevices):
        """Search if device_type correspond to likely devices and return them."""
        retval = {}
        if likelyDevices :
            for id, dev_type in self._plugin.json_data['device_types'].items():
                for refDev in likelyDevices :
                    print(u"   Validate likely device_type of {0} for {1}".format(id, refDev))
                    sensorsOK = False
                    cmdsOK = False
                    if likelyDevices[refDev]['listSensors'] :
                        for sensors in likelyDevices[refDev]['listSensors'] :
                            print(u"       Compare sensor {0} / {1}".format(sensors, dev_type['sensors']))
                            if len(sensors) == len(dev_type['sensors']) and all(i in dev_type['sensors'] for i in sensors):
                                sensorsOK = True
#                                print "    Sensor(s) OK"
                    else :
                        if not dev_type['sensors'] :
                            sensorsOK = True
#                            print "    Sensor(s) OK (No sensor)"
                    if likelyDevices[refDev]['listCmds'] :
                        for cmds in likelyDevices[refDev]['listCmds'] :
                            print(u"       Compare command {0} / {1}".format(cmds, dev_type['commands']))
                            if len(cmds) == len(dev_type['commands']) and all(i in dev_type['commands'] for i in cmds):
                                cmdsOK = True
#                                print "    Command(s) OK"
                    else :
                        if not dev_type['commands'] :
                            cmdsOK = True
#                            print "    Command(s) OK (no command)"
                    if sensorsOK and cmdsOK :
                        try :
                           len(retval[refDev])
                        except :
                            retval[refDev] = {'device_types': [], 'reference': likelyDevices[refDev]['reference']}
                        retval[refDev]['device_types'].append(id)
        return retval

    def registerDetectedDevice(self, likelyDevices):
        """Call device_detected"""
        for refDev in likelyDevices.keys() :
            for devType in likelyDevices[refDev]['device_types'] :
                print "Try to register device {0}, {1}".format(refDev, devType)
                if devType in ['rfplayer.rfp1000'] :
                    globalP = [{
                            "key" : "device",
                            "value": u"{0}".format(refDev)
                        }]
                else :
                    globalP = [{
                            "key" : "device",
                            "value": u"{0}".format(refDev)
                        }]
                self._plugin.device_detected({
                    "device_type" : devType,
                    "reference" : likelyDevices[refDev]['reference'],
                    "global" : globalP,
                    "xpl" : [],
                    "xpl_commands" : {},
                    "xpl_stats" : {}
                })

    def _handle_RFP_Data(self, client, data):
        """Handle RFP data to domogik sensor """
        if type(data) == dict and 'frame' in data :
            iType = getInfoType(data['frame'])
            if iType is not None :
                if iType.isValid :
                    devices = self._plugin.getDmgDevices(iType.dmgDevice_Id)
                    if devices != [] :
                        for dmgdev in devices :
                            for s in dmgdev['sensors']:
                                value = iType.get_RFP_data_to_sensor(dmgdev['sensors'][s])
                                print(u" Value formatted : {0} for sensor {1}".format(value, dmgdev['sensors'][s]))
                                if value is not None :
                                    self._send_sensor(dmgdev, dmgdev['sensors'][s]['id'], dmgdev['sensors'][s]['data_type'], value)
                                else :
                                    self.log.warning(u"Domogik device {0} not according to info type {1}, sensor not find.\n data : {2}\n device :".format(dmgdev['name'], iType.infoType, data, dmgdev))
                    else :
                        self.liklyDmgDevices(iType)
                        cIds = self.getIdsClient(client)
                        for cId in cIds :
                            self.monitorClients.noDmgDevice_report(cId, time.time(),  iType)
                else :
                    self.log.warning(u"Inconsistent RFP protocol ({0}) for info type {1}. data : {2}".format(data['header']['protocol'], iType.infoType, data))
            else :
                self.log.warning(u"Unknown RFP Data type : {0}".format(data))
        elif type(data) == dict and 'client' in data:
            cIds = self.getIdsClient(data['client'])
            for cId in cIds :
                client = self.getClient(cId)
                if client is not None :
                    for dmgdev in self._plugin.getDmgDevices(client.RFP_device):
                            for s in dmgdev['sensors']:
                                if 'status' in data and dmgdev['sensors'][s]['reference'] == "rfp_status":
                                    self._send_sensor(dmgdev, dmgdev['sensors'][s]['id'], dmgdev['sensors'][s]['data_type'], data['status'])
        else:
            self.log.warning(u"Bad RFP Data format : {0}".format(data))

    def processRequest(self, request, data):
        """Callback come from MQ (request with reply)"""
        report = {'error' : u"Unknown request <{0}>, data : {1}".format(request, data)}
        reqRef = request.split('.')
        if reqRef[0] == 'manager' :
            if reqRef[1] == 'getstatus' :
                report = self.getManagerInfo()
        if reqRef[0] == 'client' :
            if 'rfplayerID' in data :
                client = self.getClient(data['rfplayerID'])
                if client is not None :
                    if reqRef[1] == 'getinfos' :
                        report = client.getInfos()
                    elif reqRef[1] == 'updatefirmware' :
                        report = client.RebuildFirmware(data)
                    elif reqRef[1] == 'startmonitorclient':
                        report = self.monitorClients.startMonitorClient(data["rfplayerID"])
                    elif reqRef[1] == 'stopmonitorclient':
                        report = self.monitorClients.stopMonitorClient(data["rfplayerID"])
                else : report['error'] = u"<{0}>, Unknown RFPlayer dongle, data : {1}".format(request, data)
            else : report['error'] = u"<{0}>, Invalid data format : {1}".format(request, data)
        return report

    def getManagerInfo(self):
        """ Return all manger information """
        report = {}
        report['status'] = 'alive'
        report['rfPlayers'] = []
        for cId in self.rfpClients :
            info = self.rfpClients[cId].getState()
            info['rfplayerID'] = cId
            info['name'] = self.rfpClients[cId].domogikDevice
            info['dmgDevices'] = self._plugin.getDmgDevices(self.rfpClients[cId].domogikDevice)
            info['monitored'] = self.monitorClients.getFileName(cId) if self.monitorClients.isMonitored(cId) else ''
            report['rfPlayers'].append(info)
        report['error'] = ''
        return report

    def publishRFPlayerMsg(self, rfPLayer, category='rfplayer.client.state', data={}):
        """Report a message from a RFPLayer, default is status of RFPlayer"""
        cIds = self.getIdsClient(rfPLayer)
        for cId in cIds :
            if category == 'rfplayer.client.state':
                info = rfPLayer.getInfos()
                info['name'] = self.rfpClients[cId].domogikDevice
                info['dmgDevices'] = self._plugin.getDmgDevices(self.rfpClients[cId].domogikDevice)
                info['monitored'] = self.monitorClients.getFileName(cId) if self.monitorClients.isMonitored(cId) else ''
            else : info = {}
            info['rfplayerID'] = cId
            info.update(data)
            self._plugin.publishMsg(category, info)

class Timer():
    """
    Timer will call a callback function each n seconds
    """

    def __init__(self, time, cb, plugin):
        """
        Constructor : create the internal timer
        @param time : time of loop in second
        @param cb : callback function which will be call eact 'time' seconds
        """
        self._stop = threading.Event()
        self._timer = self.__InternalTimer(time, cb, self._stop, plugin.log)
        self._plugin = plugin
        self.log = plugin.log
        plugin.register_timer(self)
        plugin.register_thread(self._timer)
        self.log.debug(u"New timer created : %s " % self)

    def start(self):
        """
        Start the timer
        """
        self._timer.start()

    def get_stop(self):
        """ Returns the threading.Event instance used to stop the Timer
        """
        return self._stop

    def get_timer(self):
        """
        Waits for the internal thread to finish
        """
        return self._timer

    def __del__(self):
        self.log.debug(u"__del__ TimerManager")
        self.stop()

    def stop(self):
        """
        Stop the timer
        """
        self.log.debug(u"Timer : stop, try to join() internal thread")
        self._stop.set()
        self._timer.join()
        self.log.debug(u"Timer : stop, internal thread joined, unregister it")
        self._plugin.unregister_timer(self._timer)

    class __InternalTimer(threading.Thread):
        '''
        Internal timer class
        '''
        def __init__(self, time, cb, stop, log):
            '''
            @param time : interval between each callback call
            @param cb : callback function
            @param stop : Event to check for stop thread
            '''
            threading.Thread.__init__(self)
            self._time = time
            self._cb = cb
            self._stop = stop
            self.name = "internal-timer"
            self.log = log

        def run(self):
            '''
            Call the callback every X seconds
            '''
            # wait first time set
            self._stop.wait(self._time)
            while not self._stop.isSet():
                self._cb()
                self._stop.wait(self._time)

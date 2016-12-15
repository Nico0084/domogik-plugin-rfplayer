# !/usr/bin/python
#-*- coding: utf-8 -*-

import traceback

from domogik_packages.plugin_rfplayer.lib.infotypes import *
from domogik_packages.plugin_rfplayer.lib.rfp1000 import SerialRFP1000

RFP_CLIENTS_DEVICES = ["rfplayer.rfp1000"]

class RFPlayerException(Exception):
    """
    RFPlayer exception
    """
    def __init__(self, value):
        Exception.__init__(self)
        self.value = u"RFPlayer exception" + value

    def __str__(self):
        return repr(self.value)

def getRFPId(device):
    """ Return key RFPLayer id for rfplClients list."""
    if device.has_key('name') and device.has_key('id'):
        return "{0}.{1}".format(device['name'], device['id'])
    else : return None

def checkIfConfigured(deviceType,  device):
    """ Check if device_type have his all paramerter configured.
        Methode must be update for all existing RFPLayer device_type in json
    """
    if deviceType in RFP_CLIENTS_DEVICES :
        if device["parameters"]["device"]["value"] !="" : return True
        else : return False
    return False

class RFPManager(object):

    """" Manager RFPlayer(s).
    """
    def __init__ (self, plugin, cb_send_sensor) :
        """Init RFPlayer manager client"""
        self._plugin = plugin
        self._send_sensor = cb_send_sensor
        self._stop = plugin.get_stop()  # TODO : pas forcement util ?
        self.rfpClients = {} # list of all RFPlayer
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
        return self._plugin.get_stop(),

    def _del__(self):
        """Delete all RFPLayer CLients"""
        print u"try __del__ rfpClients"
        for id in self.rfpClients : self.rfpClients[id] = None

    def closeClients(self):
        """Close all RFPLayer CLients"""
        self.log.info(u"Closing RFPManager.")
        for id in self.rfpClients : self.rfpClients[id].close()

    def sendRFPcmd(self,  clID,  cmd):
        """Envoie une commmande au server NUT"""

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
                        self.rfpClients[clID] = SerialRFP1000(self.log, self._plugin.get_stop(),
                                                              dmgDevice["parameters"]["device"]["value"],
                                                              self._handle_RFP_Data, self._plugin.register_thread)
                    else :
                        self.log.error(u"Manager RFPLayer : RFPLayer Client type {0} not exist, not added.".format(clID))
                        return False
                    self.log.info(u"Manager RFPLayer : created new client {0}.".format(clID))
                    self.rfpClients[clID].open()
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

    def getIdsClient(self, idToCheck):
        """Get RFPLayer client key ids."""
        retval =[]
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
                self.log.debug (u"No key id type, search {0} in devices {1}".format(findId, self.rfpClients.keys()))
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

    def getCliDmgDevices(self, id, dmgDevices):
        """ Return domogik device of client."""
        for cId in self.rfpClients:
            for device in dmgDevices:
                if getRFPId(device) == id:
                    return device
        return None

    def _handle_RFP_Data(self, data):
        """Handle RFP data to domogik sensor """
        if type(data) == dict and 'frame' in data:
            iType = getInfoType(data['frame'])
            if iType is not None :
                if iType.isValid :
                    for dmgdev in self._plugin.getDmgDevices(iType.dmgDevice_Id):
                        for s in dmgdev['sensors']:
                            value = iType.get_RFP_data_to_sensor(dmgdev['sensors'][s])
                            print(u" Value formatted : {0} for sensor {1}".format(value, dmgdev['sensors'][s]))
                            if value is not None :
                                self._send_sensor(dmgdev, dmgdev['sensors'][s]['id'], dmgdev['sensors'][s]['data_type'], value)
                else :
                    self.log.warning(u"Inconsistent RFP protocol ({0}) for info type {1}. data : {2}".format(data['header']['protocol'], iType.infoType, data))
            else :
                self.log.warning(u"Unknown RFP Data type : {0}".format(data))
        else:
            self.log.warning(u"Bad RFP Data format : {0}".format(data))

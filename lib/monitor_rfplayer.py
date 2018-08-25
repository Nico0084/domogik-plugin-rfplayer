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

import threading
from datetime import datetime
import time
from domogik_packages.plugin_rfplayer.lib.defs import getRFPId, RFPlayerException
from collections import deque
import pprint
import traceback

class RFPlayerMonitorException(RFPlayerException):
    """"RFPlayer monitor client manager exception  class"""

    def __init__(self, value):
        RFPlayerException.__init__(self, value)
        self.msg = "RFPlayer monitor client exception: {0}".format(value)

class ManageMonitorClient(threading.Thread):
    """Monitor Client manager"""

    def __init__(self, rfpManager):
        """Create node(s) watch instance."""
        threading.Thread.__init__(self)
        self.name = "Manage_Monitor_Client"
        self._rfpManager = rfpManager
        self.ClientsMonitor={}
        self.__reports = deque([])
        self._pluginLog = rfpManager.log
        self._stop = rfpManager._stop
        self._running = False
        self._pluginLog.info(u'Monitor client(s) manager is initialized.')

    hasMonitored = property(lambda self: True if self.ClientsMonitor != {} else False)

    def refNode(self, homeId, nodeId):
        return getRFPId(homeId, nodeId)

    def run(self):
        """Running task"""
        self._running = True
        self._pluginLog.info(u'Monitor client(s) manager is started.')
        while not self._stop.isSet() and self._running :
            if self.__reports :
                report = self.__reports.popleft()
                try :
                    self.logClient(report['date'], report['type'], report['clientID'], report['data'])
                except :
                    self._pluginLog.warning(u"Monitor client bad report : {0}, {1}".format(traceback.format_exc(), report))
            else : self._stop.wait(0.01)
        # flush and close list nodes
        for client in self.ClientsMonitor :
            self.ClientsMonitor[client].close()
            del self.ClientsMonitor[client]
        self._pluginLog.info(u'Monitor client(s) manager is stopped.')

    def stop(self):
        """Stop all thread of monitoring"""
        self._running = False

    def mq_report(self, device, dmgId):
        """Callback from MQ message"""
        if self.hasMonitored :
            if device is not None :
                homeId = self._rfpManager.getHomeID(device['networkid'])
                if 'node' in device :
                    if self.isMonitored(homeId, device['node']) :
                        if 'instance' in device :
                            self.__reports.append({'date': datetime.now(),'type': "MQ report : ",
                                    'homeId': homeId,
                                    'nodeId': device['node'],
                                    'instance': device['instance'],
                                    'datas' : str(dmgId)})
                        else:
                            self.__reports.append({'date': datetime.now(),'type': "MQ report : ",
                                    'homeId': homeId,
                                    'nodeId': device['node'],
                                    'datas' : str(dmgId)})
            else :
                self._pluginLog.warning(u"Can't do MQ report, domogik device controler of networkId unknown : {0} ".format(device))

    def rawData_report(self, clientID, timestamp, msg):
        """Callback from client himself."""
        if self.hasMonitored :
            if self.isMonitored(clientID) :
                self.__reports.append({'clientID': clientID,
                                    'date': time.strftime('%Y-%m-%d %H:%M:%S.{0}'.format(repr(timestamp).split('.')[1][:3]), time.localtime(timestamp)),
                                    'type': "Raw recieved : ", 'data': msg})

    def noDmgDevice_report(self, clientID, timestamp, iType):
        """Callback from manager for client."""
        if self.hasMonitored :
            if self.isMonitored(clientID) :
                self.__reports.append({'clientID': clientID,
                        'date': time.strftime('%Y-%m-%d %H:%M:%S.{0}'.format(repr(timestamp).split('.')[1][:3]), time.localtime(timestamp)),
                        'type': "Data for new device {0} :".format(iType.dmgDevice_Id), 'data': iType.data})

    def writeData_report(self, clientID, timestamp, msg):
        """Callback from client himself."""
        if self.hasMonitored :
            if self.isMonitored(clientID) :
                self.__reports.append({'clientID': clientID,
                                    'date': time.strftime('%Y-%m-%d %H:%M:%S.{0}'.format(repr(timestamp).split('.')[1][:3]), time.localtime(timestamp)),
                                    'type': "Write data : ", 'data': msg})

    def isMonitored(self, clientID):
        """Return True if watch node."""
        return True if clientID in self.ClientsMonitor else False

    def getFileName(self, clientID):
        """Return expected log name file."""
        return "{0}{1}.log".format(self._rfpManager._plugin.get_data_files_directory(), clientID)

    def startMonitorClient(self, clientID):
        """Start client watch in log file."""
        retval = {'error': ''}
        client = self._rfpManager.getClient(clientID)
        if client is not None :
            fName = self.getFileName(clientID)
            if not self.isMonitored(clientID) :
                fLog = open(fName,  "w")
                self._pluginLog.info(u'Start monitor client {0} in log file : {1}.'.format(clientID,  fName))
                retval.update({'state': 'started', 'usermsg': u'Start monitor client {0} in log file.'.format(clientID), 'file': fName})
                fLog.write("{0} - Started monitor log for clientID {1}.\n".format(datetime.now(), clientID))
                infos = client.getInfos()
                fLog.write("clientID is registered in manager, state information : \n ")
                pprint.pprint(infos, stream=fLog)
                fLog.write("===============================================\n")
                fLog.close()
                fLog = open(fName,  "a")  # reopen in append mode
                self.ClientsMonitor.update({clientID : fLog})
                client.monitorID = clientID
            else :
                retval.update({'state': 'started', 'usermsg':  u'Monitor client {0} in log already started.'.format(clientID), 'file': fName})
                self._pluginLog.debug(u'Monitor client {0} in log already started.'.format(clientID))
        else :
            retval['error'] = u"Can't start Monitor, Client {0} is not registered in manager.".format(clientID)
        return retval

    def stopMonitorClient(self, clientID):
        """Stop watch for client"""
        retval = {'error': ''}
        client = self._rfpManager.getClient(clientID)
        if client is not None :
            if self.isMonitored(clientID) :
                client.monitorID = ""
                fLog = self.ClientsMonitor[clientID]
                retval.update({'state': 'stopped', 'usermsg':  u'Stop monitor client {0} in log file.'.format(clientID), 'file': self.getFileName(clientID)})
                self._pluginLog.info(u'Stop monitor client {0} in log file : {1}.'.format(clientID,  self.getFileName(clientID)))
                fLog.write("{0} - Stopped monitor log for clientID {1}.".format(datetime.now(), clientID))
                fLog.close()
                del self.ClientsMonitor[clientID]
            else :
                retval.update({'error': 'Monitor client {0} not running.'.format(clientID)})
        else :
            retval['error'] = u"Can't stop Monitor, Client {0} is not registered in manager.".format(clientID)
        return retval

    def logClient(self, date, type, clientID, args):
        """log client informations in file <clientID>.log, stored in package_plugin/data"""
        fLog = self.ClientsMonitor[clientID]
        fLog.write("{0} - {1}\n".format(date, type))
        if isinstance(args, str) :
            fLog.write(args)
        else :
            pprint.pprint(args, stream=fLog)
        fLog.write("-----------------------------------------------------------\n")

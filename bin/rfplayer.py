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

# A debugging code checking import error
try:
    from domogik.common.plugin import Plugin, PRODUCTS_PICTURES_EXTENSIONS, PACKAGES_DIR
    from domogikmq.message import MQMessage

    from domogik_packages.plugin_rfplayer.lib.rfplayer import RFPManager
    import threading
    import sys
    import os
    import traceback
except ImportError as exc :
    import logging
    logging.basicConfig(filename='/var/log/domogik/rfplayer_start_error.log',level=logging.DEBUG)
    err = "Error: Plugin Starting failed to import module ({})".format(exc)
    print err
    logging.error(err)

class RFPlayer(Plugin):
    """ Implement RFPLayer command messages
        and launch background  manager to listening rfplayer(s) events by callback
    """

    def __init__(self):
        """ Create background RFPlayer manager
        """
        Plugin.__init__(self, name = 'rfplayer')
        # check if the plugin is configured. If not, this will stop the plugin and log an error
        if not self.check_configured():
            return
        self.managerRFP = None
        self._ctrlsHBeat = None
        # Get some config value
        try:
            self.pathData = self.get_data_files_directory()
        except :
            self.log.warning('Data directory access error : {0}'.format(traceback.format_exc()))
            self.pathData = "{0}/{1}/{2}_{3}/data/".format(self.libraries_directory, PACKAGES_DIR, self._type, self._name)

        # Initialize plugin Manager
        try:
            self.managerRFP = RFPManager(self, self.send_sensor)
        except Exception as e:
            raise
            self.log.error('Error on creating RFPManager : {0}'.format(e))
            self.force_leave()
            return
        self.register_cb_update_devices(self.managerRFP.refreshDevices)
        self.add_mq_sub('device.update')
        # Start thread for starting rfplayer services
#        self._ctrlsHBeat = Timer(60, self.managerRFP.sendHbeatCtrlsState, self)
#        self._ctrlsHBeat.start()
        self.log.info('****** Init RFPlayer plugin manager completed ******')
        self.ready()

    def get_lib_directory(self):
        return "{0}/{1}_{2}/lib/".format(self.packages_directory, self._type, self._name)

    def on_message(self, msgid, content):
        #Transmit mq message to manager
        Plugin.on_message(self, msgid, content)
        #For momment no other message than devices.update handled

    def on_mdp_request(self, msg):
        # display the req message
        Plugin.on_mdp_request(self, msg)
        # call a function to reply to the message depending on the header
        action = msg.get_action().split(".")
        handled = False
        if action[0] == 'rfplayer' :
            self.log.debug(u"Handle MQ request action <{0}>.".format(action))
            if action[1] in ["manager", "ctrl", "value"] :
                handled = True
                data = msg.get_data()
                report = self.managerRFP.processRequest("{0}.{1}".format(action[1], action[2]),  msg.get_data())
                # send the reply
                reply_msg = MQMessage()
                reply_msg.set_action("{0}.{1}.{2}".format(action[0], action[1], action[2]))
                for k, item in report.items():
                    reply_msg.add_data(k, item)
                self.reply(reply_msg.get())
                if "ack" in  data and data['ack'] == "pub":
                    self.publishMsg("{0}.{1}.{2}".format(action[0], action[1], action[2]), report)
            if not handled :
                self.log.warning(u"MQ request unknown action <{0}>.".format(action))
        elif action[0] == "client" and action[1] == "cmd" :
            # action on dmg device
            data = msg.get_data()
            cmd =""
            for k in data.keys():
                if k not in ['device_id', 'command_id'] :
                    cmd = k
                    break;
            reply_msg = MQMessage()
            reply_msg.set_action('client.cmd.result')
            if cmd != "":
                device = self.managerRFP.getZWRefFromDB(data['device_id'], data['command_id'], "cmd")
                if device :
                    self.managerRFP.sendCmdToZW(device, cmd, data[cmd])
                    reply_msg.add_data('status', True)
                    reply_msg.add_data('reason', None)
                else :
                    self.log.warning(u"Abording command, no device found for command MQ: {0}".format(data))
                    reply_msg.add_data('status', False)
                    reply_msg.add_data('reason', u"Abording command, no device found for MQ command: {0}".format(data))
            else :
                self.log.warning(u"Abording command, no extra key in command MQ: {0}".format(data))
                reply_msg.add_data('status', False)
                reply_msg.add_data('reason', u"Abording command, no extra key in MQ command: {0}".format(data))

            self.log.debug(u"Reply to MQ: {0}".format(reply_msg.get()))
            self.reply(reply_msg.get())

    def getDmgDevices(self, deviceId):
        """ Search if domogik device exist for id and return it/them, else return []"""
        devices = []
        print(u"Search for dmg device : {0}".format(deviceId))
        for dmgDevice in self.devices :
            if 'device' in dmgDevice['parameters']:
                print(dmgDevice)
                if dmgDevice['parameters']['device']['value'] == deviceId :
                    print(u"Device ok")
                    devices.append(dmgDevice)
        return devices

    def send_sensor(self, device, sensor_id, dt_type, value):
        """Send pub message over MQ"""
        self.log.info(u"Sending MQ sensor id:{0}, dt type: {1}, value:{2}" .format(sensor_id, dt_type, value))
        self._pub.send_event('client.sensor',
                         {sensor_id : value})
#        if self.managerRFP is not None and self.managerRFP.monitorNodes is not None :
#            self.managerRFP.monitorNodes.mq_report(device, {u"sensorId": sensor_id, u"dt_type": dt_type, u"value": value})

    def publishMsg(self, category, content):
        self._pub.send_event(category, content)
        self.log.debug(u"Publishing over MQ <{0}>, data : {1}".format(category, content))

class Timer():
    """
    Timer will call a callback function each n seconds
    """
#    _time = 0
#    _callback = None
#    _timer = None

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
            while not self._stop.isSet():
                self._cb()
                self._stop.wait(self._time)


if __name__ == "__main__":
    RFPlayer()

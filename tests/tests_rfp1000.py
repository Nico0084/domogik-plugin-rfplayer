#!/usr/bin/python
# -*- coding: utf-8 -*-

from domogik.xpl.common.plugin import Plugin
from domogik.tests.common.helpers import Printc
from domogik.tests.common.plugintestcase import PluginTestCase
from domogik.tests.common.testplugin import TestPlugin
from domogik.tests.common.testdevice import TestDevice
from domogik.tests.common.testsensor import TestSensor
from domogik.common.utils import get_sanitized_hostname
from datetime import datetime
import unittest
import sys
import os
import json
import traceback
# TODO : remove
import time

class RFPlayerTestCase(PluginTestCase):

    def __init__(self, testname, plugin, name, configuration, sensorsTest=[]):
        PluginTestCase.__init__(self, testname, plugin, name, configuration)
        self.sensorsTest = sensorsTest

    def test_0100_dummy(self):
        self.assertTrue(True)

    def test_0100_rfplayer(self):
        """ Test if the RFPlayer sensor is sent when a frame is received
        """
        global timer_status
        global device
        global device_id

        self.testDevices = []

        # do the test
        Printc.infob(u"Check that a MQ message for RFPlayer status started is sent.")

        data = {"rfp_status" : 1}
        self.assertTrue(self.wait_for_mq(device_id = device_id,
                                          data = data,
                                          timeout = timer_status * 2))
        time.sleep(1)
        Printc.infob(u"Check that the values of the MQ message has been inserted in database")
        sensor = TestSensor(device_id, "rfp_status")
        self.assertTrue(sensor.get_last_value()[1] == str(data['rfp_status']))

    def test_0110_device_sensors(self):
        """ Test if the RFPlayer sensor infoType 4 5 6 7 9 is sent when a frame is received
        """
        for device in self.sensorsTest:
            Printc.infob(u"Check that a MQ message for all the sensors of device <{0}> id <{1}> are sent.".format(device['name'], device['device_id']))
            data = {}
            for value in device['values'] :
            # do the test
                Printc.infob(u"Check that a MQ message for the sensor <{0}> frame received is sent.".format(value["sensor"]))
                data[value["sensor"]] = value["value"]
            self.assertTrue(self.wait_for_mq(device_id = device['device_id'],
                                              data = data,
                                              timeout = device['timeout']))
            time.sleep(1)
            for value in device['values'] :
                Printc.infob(u"Check that the values of the MQ message for the sensor <{0}> has been inserted in database".format(value["sensor"]))
                sensor = TestSensor(device['device_id'], value["sensor"])
                self.assertTrue(sensor.get_last_value()[1] == str(value["value"]))

def createDevice(dataJson):
    td = TestDevice()
    # create a test device
    try:
        params = td.get_params(client_id, dataJson["device_type"])
        # fill in the params
        params["device_type"] = dataJson["device_type"]
        params["name"] = dataJson['name']
        params["reference"] = "reference"
        params["description"] = "description"
        # global params
        for the_param in params['global']:
            for p in dataJson["parameters"] :
                if the_param["key"] == p["key"] :
                    the_param["value"] = p["value"]
                    break
        print params['global']
        # xpl params
        pass # there are no xpl params for this plugin
        # create
        return td.create_device(params)['id'], td
    except:
        Printc.err(u"Error while creating the test devices {0} : {1}".format(device, traceback.format_exc()))
        return False, td

if __name__ == "__main__":

    test_folder = os.path.dirname(os.path.realpath(__file__))

    ### global variables
    device = "/dev/rfplayer"
    timer_status = 30

    # set up the features
    plugin = Plugin(name = 'test',
                           daemonize = False,
                           parser = None,
                           test  = True)

    # set up the plugin name
    name = "rfplayer"

    # set up the configuration of the plugin
    # configuration is done in test_0010_configure_the_plugin with the cfg content
    # notice that the old configuration is deleted before
    cfg = {'configured': True, 'auto_startup': 'N'}

    # specific configuration for test mdode (handled by the manager for plugin startup)
    cfg['test_mode'] = True
    cfg['test_option'] = "{0}/x10_protocol_data.json".format(test_folder)

    ### start tests
    # load the test devices class
    td = TestDevice()

    # delete existing devices for this plugin on this host
    client_id = "{0}-{1}.{2}".format("plugin", name, get_sanitized_hostname())
    try:
        td.del_devices_by_client(client_id)
    except:
        Printc.err(u"Error while deleting all the test device for the client id '{0}' : {1}".format(client_id, traceback.format_exc()))
        sys.exit(1)

    # create a test device
    try:
        #device_id = td.create_device(client_id, "test_device_RFPlayer", "RFPlayer.electric_meter")

        params = td.get_params(client_id, "rfplayer.rfp1000")

        # fill in the params
        params["device_type"] = "rfplayer.rfp1000"
        params["name"] = "test_device_RFPlayer"
        params["reference"] = "reference"
        params["description"] = "description"
        # global params
        for the_param in params['global']:
            if the_param['key'] == "timer_status":
                the_param['value'] = timer_status
            if the_param['key'] == "device":
                the_param['value'] = device
        print params['global']
        # xpl params
        pass # there are no xpl params for this plugin
        # create
        device_id = td.create_device(params)['id']

    except:
        Printc.err(u"Error while creating the test devices : {0}".format(traceback.format_exc()))
        sys.exit(1)

    ### prepare and run the test suite
    suite = unittest.TestSuite()
    # check domogik is running, configure the plugin
    suite.addTest(RFPlayerTestCase("test_0001_domogik_is_running", plugin, name, cfg))
    suite.addTest(RFPlayerTestCase("test_0010_configure_the_plugin", plugin, name, cfg))

    # start the plugin
    suite.addTest(RFPlayerTestCase("test_0050_start_the_plugin", plugin, name, cfg))

    # do the specific plugin tests
    suite.addTest(RFPlayerTestCase("test_0100_rfplayer", plugin, name, cfg))

    # do the specific device tests
    jsonFile = "x10_protocol_result.json"
    try:
        json_fp = open("{0}/{1}".format(test_folder, jsonFile))
        dataJson = json.load(json_fp)
        Printc.infob(u"Data for specific tests are loaded from {0}".format(jsonFile))
        json_fp.close()
    except:
        Printc.err(u"Error while loading json tests {0} : {1}".format("{0}/{1}".format(test_folder, jsonFile), traceback.format_exc()))
    else :
        for device in dataJson :
            dev_id, td = createDevice(device)
            device['device_id'] = dev_id
            time.sleep(5) # due to high DB flow, wait 5s
        suite.addTest(RFPlayerTestCase("test_0110_device_sensors", plugin, name, cfg, dataJson))

# do some tests comon to all the plugins
    #suite.addTest(RFPlayerTestCase("test_9900_hbeat", plugin, name, cfg))
    suite.addTest(RFPlayerTestCase("test_9990_stop_the_plugin", plugin, name, cfg))

    # quit
    res = unittest.TextTestRunner().run(suite)
    if res.wasSuccessful() == True:
        rc = 0   # tests are ok so the shell return code is 0
    else:
        rc = 1   # tests are ok so the shell return code is != 0
    plugin.force_leave(return_code = rc)


#!/usr/bin/python
# -*- coding: utf-8 -*-

from domogik.tests.common.testsensor import TestSensor

class Test_Sensor(object):

    def __init__(self, plugintest, device_id, sensor_id, dataJson):
        self._plugintest = plugintest
        self._device_id = device_id
        self._sensor_id = sensor_id
        self._dataJson = dataJson

    def do_tests(self):
        global device
        global device_id

        # do the test
        print(u"Check that a MQ message for the frame received is sent.")

        data = {"rfp_status" : 1}
        self._plugintest.assertTrue(self._plugintest.wait_for_mq(device_id = device_id,
                                          data = data,
                                          timeout = timer_status * 4))
        time.sleep(1)
        print(u"Check that the values of the MQ message has been inserted in database")
        sensor = TestSensor(device_id, "rfp_status")
        self._plugintest.assertTrue(sensor.get_last_value()[1] == str(data['rfp_status']))


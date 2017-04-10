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
RFP_CLIENTS_DEVICES = ["rfplayer.rfp1000"]

class RFPlayerException(Exception):
    """
    RFPlayer exception
    """
    def __init__(self, value):
        Exception.__init__(self)
        self.value = u"RFPlayer exception: {0}".format(value)

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

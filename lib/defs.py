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

# Header definition
SYNCHEADER = ["Z", "I"]
SOURCEDESTQUALIFIER = ["A", "O"] # Data form ASCII or BINARY
SOURCEDEST = 1
QUALIFIER_COMMANQ = "++"
QUALIFIER_RECEPT = "--"
QUALIFIER_XML = "22"
QUALIFIER_JSON = "33"
QUALIFIER_TEXT = "44"
TERMINATOR = "\r"

# data format
XMLDATA = "XML"
JSONDATA = "JSON"
TEXTDATA = "TEXT"

# Protocoles Ids
X10 = "X10"
RTS = "RTS"
VISONIC = "VISONIC"
BLYSS = "BLYSS"
CHACON = "CHACON"
OREGONV1 = "OREGONV1"
OREGONV2 = "OREGONV2"
OREGONV3_OWL = "OREGONV3/OWL"
DOMIA = "DOMIA"
X2D = "X2D"
KD101 = "KD101"
PARROT = "PARROT"

COMMANDS = {"HELLO": {},
            "STATUS":{
                    0: ["", "SYSTEM", "RADIO", "TRANSCODER", "PARROT"],
                    1: ["", "TEXT", "XML", "JSON"]
                    },
            "FREQ" : {
                "H":["0", "868950", "868350"],
                "L":["0", "433420", "433920"]
                },
            "SELECTIVITY":{
                "H":["0", "1", "2", "3", "4", "5"],
                "L":["0", "1", "2", "3", "4", "5"]
                },
            "SENSITIVITY":{
                "H":["0", "1", "2", "3", "4"],
                "L":["0", "1", "2", "3", "4"]
                },
            "DSPTRIGGER":{
                "H":[str(x) for x in range(4,21)],
                "L":[str(x) for x in range(4,21)]
                },
            "RFLINKTRIGGER":{
                "H":[str(x) for x in range(4,21)],
                "L":[str(x) for x in range(4,21)]
                },
            "LBT":[str(x) for x in range(0,31)],
            "SETMAC": {},
            "FACTORYRESET": ["","ALL"],
            "FORMAT": ["OFF", "BINARY", "HEXA", "HEXA FIXED", TEXTDATA, XMLDATA, JSONDATA, "RFLINK OFF", "RFLINK BINARY"],
            "RECEIVER": ["*", X10, RTS, VISONIC, BLYSS, CHACON, OREGONV1, OREGONV2, OREGONV3_OWL, DOMIA, X2D, KD101, PARROT],
            "REPEATER": ["*", X10, RTS, VISONIC, BLYSS, CHACON, OREGONV1, OREGONV2, OREGONV3_OWL, DOMIA, X2D, KD101, "ON", "OFF"],
            "LEDACTIVITY": ["0", "1"],
            "PARROTLEARN": ["", "ON", "OFF"],
            "REMAPPING": {
                0: "PARROT",
                1: ["ONOFF", "CLEAR"]
                },
            "TRANSCODER": {
                0: ["", "ENTRY"],
                1: ["TO", "CLEAR"]
                }
            }

INFOTYPE = {
    0:{
        "protocoles": [X10, DOMIA, PARROT],
        "decription": "Used by X10 / DOMIA LITE protocol / PARROT",
        "parameters" :[
            "subType",
            "id"
            ]
    },
    1:{
        "protocoles": [X10, CHACON, KD101, BLYSS],
        "decription": "Used by X10 (24/32 bits ID), CHACON , KD101, BLYSS",
        "parameters" :[
            "subType",
            "id_lsb",
            "id_msb"
            ]
    },
    2:{
        "protocoles": [VISONIC],
        "decription": "Used by VISONIC",
        "parameters" :[
            "subType",
            "id_lsb",
            "id_msb",
            "qualifier"
            ]
    },
    3:{
        "protocoles": [RTS],
        "decription": "Used by RTS protocol",
        "parameters" :[
            "subType",
            "id_lsb",
            "id_msb",
            "qualifier"
            ]
    },
    4:{
        "protocoles": [OREGONV1, OREGONV2, OREGONV3_OWL],
        "decription": "Thermo/Hygro sensors",
        "parameters" :[
            "subType",
            "id_PHY",
            "adr_channel",
            "qualifier",
            "temp",
            "hydro"
            ]
    },
    5:{
        "protocoles": [OREGONV1, OREGONV2, OREGONV3_OWL],
        "decription": "Atmospheric pressure sensors",
        "parameters" :[
            "subType",
            "id_PHY",
            "adr_channel",
            "qualifier",
            "temp",
            "pressure",
            "hydro"
            ]
    },
    6:{
        "protocoles": [OREGONV1, OREGONV2, OREGONV3_OWL],
        "decription": "Wind sensors",
        "parameters" :[
            "subType",
            "id_PHY",
            "adr_channel",
            "qualifier",
            "speed",
            "direction"
            ]
    },
    7:{
        "protocoles": [OREGONV1, OREGONV2, OREGONV3_OWL],
        "decription": "UV sensors",
        "parameters" :[
            "subType",
            "id_PHY",
            "adr_channel",
            "UV"
            ]
    },
    8:{
        "protocoles": [OREGONV3_OWL],
        "decription": "Energy/power sensors",
        "parameters" :[
            "subType",
            "id_PHY",
            "adr_channel",
            "qualifier",
            "Energy_lsb",
            "Energy_msb",
            "Power",
            "P1",
            "P2",
            "P3"
            ]
    },
    9:{
        "protocoles": [OREGONV1, OREGONV2, OREGONV3_OWL],
        "decription": "Rain sensors",
        "parameters" :[
            "subType",
            "id_PHY",
            "adr_channel",
            "TotalRain_lsb",
            "TotalRain_msb",
            "Rain"
            ]
    },
    10:{
        "protocoles": [X2D],
        "decription": "Thermostats",
        "parameters" :[
            "subType",
            "id_lsb",
            "id_msb",
            "qualifier",
            "Function",
            "State"
            ]
    },
    11:{
        "protocoles": [X2D],
        "decription": "Alarm",
        "parameters" :[
            "subType",
            "id_lsb",
            "id_msb",
            "qualifier"
            ]
    }
}

print INFOTYPE

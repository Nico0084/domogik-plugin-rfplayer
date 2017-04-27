#!/usr/bin/python
# -*- coding: utf-8 -*-

import traceback

# Protocols Ids

RF_PROTOCOLS = {"0" : {"name": "UNKNOWN", "freq": [], "infotype": []},
                "1" : {"name": "VISONIC_", "freq": ["433"], "infotype": ["0", "1"]},
                "2" : {"name": "VISONIC", "freq": ["868"], "infotype": ["2"]},
                "3" : {"name": "CHACON", "freq": ["433"], "infotype": ["1"]},
                "4" : {"name": "DOMIA", "freq": ["433"], "infotype": ["1"]},
                "5" : {"name": "X10", "freq": ["433"], "infotype": ["4", "5", "6", "7", "9"]},
                "6" : {"name": "X2D", "freq": ["433"], "infotype": ["0"]},
                "7" : {"name": "X2D", "freq": ["868"], "infotype": ["8"]},
                "8" : {"name": "X2D_SHUTTER", "freq": ["868"], "infotype": ["10", "11"]},
                "9" : {"name": "X2D_HA_ELEC", "freq": ["868"], "infotype": ["3"]},
                "10": {"name": "X2D_HA_GAS", "freq": ["868"], "infotype": ["1"]},
                "12": {"name": "BLYSS", "freq": ["433"], "infotype": ["1"]},
                "13": {"name": "PARROT", "freq": ["433", "868"], "infotype": ["0"]},
                "14": {"nameid": "reserved", "freq": [], "infotype": []},
                "15": {"name": "reserved", "freq": [], "infotype": []},
                "16": {"name": "KD101", "freq": ["433"], "infotype": ["1"]}
                }

PROTOCOLS = {"0": {"name": "UNKNOWN",
                                    "infotype": [],
                                    "cmd":{}},
                      "1": {"name": "X10",
                                "infotype": ["0", "1"],
                                "cmds":{
                                    "switch":{
                                        "0": "OFF {0} X10",
                                        "1": "ON {0} X10",
                                        },
                                    "switch_all":{
                                        "0": "ALL_OFF {0} X10",
                                        "1": "ALL_ON {0} X10",
                                        },
                                    "dimmer":{
                                        "0": "DIM {0} X10 %{1}",
                                        "1": "BRIGHT {0} X10 %{1}",
                                        }
                                    }
                            },
                      "2": {"name": "VISONIC", "infotype": ["2"]},
                      "3": {"name": "BLYSS",
                                "infotype": ["1"],
                                "cmds":{
                                    "switch":{
                                        "0": "OFF {0} BLYSS",
                                        "1": "ON {0} BLYSS",
                                        },
                                    "dimmer":{
                                        "0": "DIM {0} BLYSS %{1}",
                                        "1": "BRIGHT {0} BLYSS %{1}",
                                        }
                                    }
                            },
                      "4": {"name": "CHACON",
                                "infotype": ["1"],
                                "cmds":{
                                    "switch":{
                                        "0": "OFF {0} CHACON",
                                        "1": "ON {0} CHACON",
                                        },
                                    "switch_all":{
                                        "0": "ALL_OFF {0} CHACON",
                                        "1": "ALL_ON {0} CHACON",
                                        },
                                    "dimmer":{
                                        "0": "DIM {0} CHACON %{1}",
                                        "1": "BRIGHT {0} CHACON %{1}",
                                        }
                                    }
                            },
                      "5": {"name": "OREGON",
                                "infotype": ["4", "5", "6", "7", "9"],
                                "cmds":{}
                            },
                      "6": {"name": "DOMIA", "infotype": ["0"]},
                      "7": {"name": "OWL", "infotype": ["8"]},
                      "8": {"name": "XD2", "infotype": ["10", "11"]},
                      "9": {"name": "RTS", "infotype": ["3"]},
                      "10": {"name": "KD101", "infotype": ["1"]},
                      "11": {"name": "PARROT", "infotype": ["0"]}
                    }

def getInfoType(data) :
    """Return infoType object of RFP data"""
    if data['header']['infoType'] == "0" : return InfoType0(data)
    elif data['header']['infoType'] == "1" : return InfoType1(data)
    elif data['header']['infoType'] == "2" : return InfoType2(data)
    elif data['header']['infoType'] == "3" : return InfoType3(data)
    elif data['header']['infoType'] == "4" : return InfoType4(data)
    elif data['header']['infoType'] == "5" : return InfoType5(data)
    elif data['header']['infoType'] == "6" : return InfoType6(data)
    elif data['header']['infoType'] == "7" : return InfoType7(data)
    elif data['header']['infoType'] == "8" : return InfoType8(data)
    elif data['header']['infoType'] == "9" : return InfoType9(data)
    elif data['header']['infoType'] == "10" : return InfoType10(data)
    elif data['header']['infoType'] == "11" : return InfoType11(data)
    return None

def getInfoTypesFromProtocol(protocol):
    """ Return infotype(s) corresponding to protocol"""
    if protocol in PROTOCOLS :
        return PROTOCOLS[protocol]['infotype']
    return []

def getInfoTypeFromCmd(device, cmd, command, values):
    """" return infoType corresponding to a domogik cmd"""
    data = getRfpDataFromDmgDevice(device)
    if data is not None :
        iTypes = getInfoTypesFromProtocol(data['header']['protocol'])
        print(iTypes)
        if iTypes != []:
            for i in iTypes:
                data['header']['infoType'] = i
                iType = getInfoType(data)
                print(iType)
                if iType.get_cmd_to_RFP_data(cmd, command, values) is not None:
                    return iType
    return None

def getRfpDataFromDmgDevice(device):
    protocol = device['device_type_id'].split(".")[1]
    if protocol in PROTOCOLS :
        data = {"header": {
                    "frameType": "0", "dataFlag": "1", "rfLevel": "", "floorNoise": "", "rfQuality": "",
                    "protocol": protocol,
                    "protocolMeaning": PROTOCOLS[protocol]["name"],
                    "infoType": "255",
                    "frequency": "868950"},
                "infos": {"subType": "0", "subTypeMeaning": "", "id": device['parameters']['device']['value'],
                    "qualifier": "",
                    "qualifierMeaning": {}}}
        return data
    else :
        return None

class InfoType(object) :
    """Base class to handle InfoType"""

    infoType = "255"

    def __init__(self, data) :
        """ Initialize InfoType object with RFP Data
            @param data : RFPlayer data in JSON.
        """
        self.subType = "0"
        self.data = data

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return []

        self.log.warning(u"Base InfoType Unknown protocol dmg device id: {0}".format(self.data))
        return ""

    @property
    def protocol_name(self):
        """ Return protocol name from data"""
        return self.data['header']['protocolMeaning']

    @property
    def dmgDevice_Id(self):
        """ Return domogik device id depending of data protocol"""
        return ""

    @property
    def isValid(self):
        """ Check coherente data protocol"""
        return  self.data['header']['protocol'] in self.protocols_Id

    def get_RFP_data_to_sensor(self, sensor):
        """Return sensor value from RFP data
            @param sensor : the domogik sensor data_type dict.
            @return : value in data_type format, else None.
        """
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        return []

    def get_cmd_to_RFP_data(self, cmd, command,  values):
        """Return command  RFP data from dmg command value
            @param cmd : the domogik command name reference.
            @param command : the domogik command data_type dict.
            @param values : dict of parameters and its value of command.
            @return : ASCII Command format, else None.
        """
        return None

    def get_Available_Commands(self):
        """Return all dmg command id available by this infotype, for device detection"""
        return []

class InfoType0(InfoType) :
    """Info Type for X10, DOMIA, PARROT protocol"""

    infoType = "0"

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return ["1", "6", "11"]

    @property
    def dmgDevice_Id(self):
        """ Return domogik device id depending of data protocol"""
        if self.data['header']['protocol'] in self.protocols_Id:
            return self.data['infos']['id']
        return ""

    def get_RFP_data_to_sensor(self, sensor):
        """Return sensor value from RFP data"""
        try :
            if sensor['reference'] in ["switch", "switch_all", "bright_dim"] :
                if self.data['infos']['subType'] in ["0", "2", "4"] : # 0: OFF, 2: BRIGHT, 4: ALL_ OFF
                    return "0"
                elif self.data['infos']['subType'] in ["1", "3", "5"] : # 1: ON, 3: DIM, 5 : ALL_ ON
                    return "1"
        except :
            pass
        return None

    def get_cmd_to_RFP_data(self, cmd, command,  values):
        """Return command  RFP data from dmg command value
            @param cmd : the domogik command name reference.
            @param command : the domogik command data_type dict.
            @param values : dict of parameters and its value of command.
            @return : ASCII Command format, else None.
        """
        try :
            print(self.data)
            print(cmd, command, values)
            if cmd == "dimmer" :
                cmdLine = PROTOCOLS[self.data['header']['protocol']]['cmds'][cmd][values['value']].format(self.data['infos']['id'], values['level'])
            else :
                cmdLine = PROTOCOLS[self.data['header']['protocol']]['cmds'][cmd][values['value']].format(self.data['infos']['id'])
            print(cmdLine)
            return cmdLine
        except :
            print(u"{0}".format(traceback.format_exc()))
        return None

    def get_Available_Commands(self):
        """Return all dmg command id available by this infotype, for device detection"""
        return [["switch", "switch_all", "dimmer"]]


class InfoType1(InfoType0) :
    """Info Type for X10, BLYSS, CHACON, KD101 protocol"""

    infoType = "1"

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return ["1", "3", "4", "10"]

    def get_RFP_data_to_sensor(self, sensor):
        """Return sensor value from RFP data"""
        try :
            if sensor['reference'] in ["switch", "switch_all"] :
                if self.data['infos']['subType'] in ["0", "4"] : # 0: OFF, 4: ALL_ OFF
                    return "0"
                elif self.data['infos']['subType'] in ["1", "5"] : # 1: ON, 5 : ALL_ ON
                    return "1"
        except :
            pass
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        if self.data['header']['protocol'] in ["1", "4"] : # X10, CHACON
            return [["switch", "rf_quality"]]
        elif self.data['header']['protocol'] in ["3", "10"] : # BLYSS, KD101
            return [["switch", "switch_all", "rf_quality"]]
        return []

    def get_Available_Commands(self):
        """Return all dmg command id available by this infotype, for device detection"""
        if self.data['header']['protocol'] in ["1", "4"] : # X10, CHACON
            return [["switch", "switch_all", "dimmer"]]
        elif self.data['header']['protocol'] in ["3", "10"] : # BLYSS, KD101
            return [["switch"]]
        return []

class InfoType2(InfoType) :
    """Info Type for VISONIC protocol"""

    infoType = "2"

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return ["2"]

    @property
    def dmgDevice_Id(self):
        """ Return domogik device id depending of data protocol"""
        if self.data['header']['protocol'] in self.protocols_Id:
            return "{0}.{1}".format(self.data['infos']['id'], self.data['infos']['subType'])
        return ""

    def get_RFP_data_to_sensor(self, sensor):
        """Return sensor value from RFP data"""
        try :
            qualifier = int(self.data['infos']['qualifier'])
            if self.data['infos']['subType'] == "0" : # detector/sensor/ PowerCode device
               # D0 : Tamper Flag, D1: Alarm Flag, D2: Low Batt Flag
                if sensor['data_type'] == 'DT_OpenClose' :
                    return 1 if qualifier & 1 else 0
                elif sensor['reference'] == 'alarm' :
                    return 1 if qualifier & 2 else 0
                elif sensor['reference'] == 'low_battery' :
                    return 1 if qualifier & 4 else 0
            elif self.data['infos']['subType'] == 1 : # remote control device (MCT-234 style)
                # 5 : Left button 6 : Right button
                if sensor['reference'] == 'button_1' and (qualifier and 0x08): return 1
                elif sensor['reference'] == 'button_2' and (qualifier and 0x10) : return 1
                elif sensor['reference'] == 'button_3' and (qualifier and 0x20) : return 1
                elif sensor['reference'] == 'button_3' and (qualifier and 0x40) : return 1
        except :
            pass
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        if self.data['infos']['subType'] == "0" : # Detector/Sensor
            return [["tamper", "alarm", "low_battery", "rf_quality"]]
        elif self.data['infos']['subType'] == "1" : # remote control
            return [["button_1", "button_2", "button_3", "button_4", "rf_quality"]]
        return []

    def get_Available_Commands(self):
        """Return all dmg command id available by this infotype, for device detection"""
        if self.data['infos']['subType'] == "1" : # remote control
            return [["button_1", "button_2", "button_3", "button_4"]]
        return []

class InfoType3(InfoType0) :
    """Info Type for RTS protocol"""

    infoType = "3"

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return ["9"]

    def get_RFP_data_to_sensor(self, sensor):
        """Return sensor value from RFP data"""
        try :
            qualifier = int(self.data['infos']['qualifier'])
            if self.data['infos']['subType'] == "0" : # Shutter device
               # 1 : Down /OFF, 4 : My, 7 : Up / ON, 13 : ASSOC
                if sensor['reference'] == 'shutter' :
                    if qualifier == 1 : return 1
                    if qualifier == 7 : return 0
                if sensor['reference'] == 'push_button' :
                    if qualifier == 4 : return 1
                elif qualifier == 13 : pass # TODO: Handling ASSOCIATION command on RTS Protocol?
            elif self.data['infos']['subType'] == "1" : # portals Remote control
                # 5 : Left button 6 : Right button
                if sensor['reference'] == 'button_1' and (qualifier == 5) : return 1
                elif sensor['reference'] == 'button_2' and (qualifier == 6) : return 1
        except :
            pass
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        if self.data['infos']['subType'] == "0" : # Shutter device
            return [["shutter", "push_button", "rf_quality"]]
        elif self.data['infos']['subType'] == "1" : # portals Remote control
            return [["button_1", "button_2", "rf_quality"]]
        return []

    def get_Available_Commands(self):
        """Return all dmg command id available by this infotype, for device detection"""
        if self.data['infos']['subType'] == "0" : # Shutter device
            return [["shutter", "push_button"]]
        elif self.data['infos']['subType'] == "1" : # portals Remote control
            return [["button_1", "button_2"]]
        return []

class InfoType4(InfoType) :
    """Info Type for OREGON protocol"""

    infoType = "4"

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return ["5"]

    @property
    def dmgDevice_Id(self):
        """ Return domogik device id depending of data protocol"""
        if self.data['header']['protocol'] in self.protocols_Id:
            return "{0}.{1}.{2}".format(self.data['infos']['id_PHY'], self.data['infos']['adr'], self.data['infos']['channel'])
        return ""

    def get_RFP_data_to_sensor(self, sensor):
        """ Return sensor value from RFP data"""
        print("Format value : {0}".format(self.data))
        try :
            for mes in self.data['infos']['measures']:
                if mes['type'] == sensor['name']:
                    if sensor['data_type'] == "DT_Temp" and mes['unit'] == 'Celsius':
                        return float(mes['value'])
                    elif sensor['data_type'] == "DT_Humidity" and mes['unit'] == '%':
                        return int(mes['value'])
            if sensor['reference'] == "low_battery" :
                return int(self.data['infos']['lowBatt'])
            elif sensor['reference'] == "rf_quality" :
                return int(self.data['header']['rfQuality']) * 10
        except :
            print(u"{0}".format(traceback.format_exc()))
            pass
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        sensors = [["temperature", "low_battery", "rf_quality"]]
        for mes in self.data['infos']['measures']:
            if mes['type'] == "hygrometry" and mes['value'] != "0":
                sensors = [["temperature", "hygrometry", "low_battery", "rf_quality"]]
                break
        return sensors

class InfoType5(InfoType4) :
    """Info Type for OREGON protocol
        inherit from InfoType4 of OREGON"""

    infoType = "5"

    def get_RFP_data_to_sensor(self, sensor):
        """ Return sensor value from RFP data"""
        print("Format value : {0}".format(self.data))
        try :
            for mes in self.data['infos']['measures']:
                if mes['type'] == sensor['name']: # TODO: Check type and name correspondance on real data
                    if sensor['data_type'] == "DT_Temp" and mes['unit'] == 'Celsius':
                        return float(mes['value'])
                    elif sensor['data_type'] == "DT_Humidity" and mes['unit'] == '%':
                        return int(mes['value'])
                    elif sensor['data_type'] == "DT_Pressure" and mes['unit'] == 'hPa':
                        # convert hPa to Pa for DT_Pressure
                        return int(mes['value']) * 100
            if sensor['reference'] == "low_battery" :
                return int(self.data['infos']['lowBatt'])
            elif sensor['reference'] == "rf_quality" :
                return int(self.data['header']['rfQuality']) * 10
        except :
            print(u"{0}".format(traceback.format_exc()))
            pass
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        return [["temperature", "hygrometry", "pressure", "low_battery", "rf_quality"]]


class InfoType6(InfoType4) :
    """Info Type for OREGON protocol
        inherit from InfoType4 of OREGON"""

    infoType = "6"

    def get_RFP_data_to_sensor(self, sensor):
        """ Return sensor value from RFP data"""
        print("Format value : {0}".format(self.data))
        try :
            for mes in self.data['infos']['measures']:
                if mes['type'] == sensor['name']:  # TODO: Check type and name correspondance on real data
                    if sensor['data_type'] == "DT_Speed" and mes['unit'] == 'm/s':
                        return float(mes['value'])
                    elif sensor['data_type'] == "DT_Angle" and mes['unit'] == 'degree':
                        return int(mes['value'])
            if sensor['reference'] == "low_battery" :
                return int(self.data['infos']['lowBatt'])
            elif sensor['reference'] == "rf_quality" :
                return int(self.data['header']['rfQuality']) * 10
        except :
            print(u"{0}".format(traceback.format_exc()))
            pass
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        return [["wind_speed", "direction", "low_battery", "rf_quality"]]


class InfoType7(InfoType4) :
    """Info Type for OREGON protocol
       inherit from InfoType4 of OREGON"""

    infoType = "7"

    def get_RFP_data_to_sensor(self, sensor):
        """ Return sensor value from RFP data"""
        print("Format value : {0}".format(self.data))
        try :
            for mes in self.data['infos']['measures']:
                if mes['type'] == sensor['name']:  # TODO: Check type unit and name correspondance on real data
                    if sensor['data_type'] == "DT_Number" : # and mes['unit'] == '': # TODO: NO unit control for momment, must be checked
                        return int(mes['value'])
            if sensor['reference'] == "low_battery" :
                return int(self.data['infos']['lowBatt'])
            elif sensor['reference'] == "rf_quality" :
                return int(self.data['header']['rfQuality']) * 10
        except :
            print(u"{0}".format(traceback.format_exc()))
            pass
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        return [["uv", "low_battery", "rf_quality"]]

class InfoType8(InfoType) :
    """Info Type for OWL protocol"""

    infoType = "8"

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return ["7"]

    @property
    def dmgDevice_Id(self):
        """ Return domogik device id depending of data protocol"""
        if self.data['header']['protocol'] in self.protocols_Id:
            return "{0}.{1}.{2}".format(self.data['infos']['id_PHY'], self.data['infos']['adr'], self.data['infos']['channel'])
        return ""

    def get_RFP_data_to_sensor(self, sensor):
        """ Return sensor value from RFP data"""
        print("Format value : {0}".format(self.data))
        # TODO: Handle qualifier ? D1 = 0 : Only the tatal instaneous power is given, D1 = 1 : power in each imput 1,2,3
        try :
            for mes in self.data['infos']['measures']:
                if mes['type'] == sensor['name']:  # TODO: Check type and name correspondance on real data
                    if sensor['data_type'] == "DT_ActiveEnergy" and mes['unit'] == 'Wh':
                        return int(mes['value'])
                    elif sensor['data_type'] == "DT_Power" and mes['unit'] == 'W': # power, P1, P2, P3
                        return int(mes['value'])
            if sensor['reference'] == "low_battery" :
                return int(self.data['infos']['lowBatt'])
            elif sensor['reference'] == "rf_quality" :
                return int(self.data['header']['rfQuality']) * 10
        except :
            print(u"{0}".format(traceback.format_exc()))
            pass
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        return [["energy", "power", "P1", "P2", "P3", "low_battery", "rf_quality"]]

class InfoType9(InfoType4) :
    """Info Type for OREGON protocol
       inherit from InfoType4 of OREGON"""

    infoType = "9"

    def get_RFP_data_to_sensor(self, sensor):
        """ Return sensor value from RFP data"""
        print("Format value : {0}".format(self.data))
        try :
            for mes in self.data['infos']['measures']:
                if mes['type'] == sensor['name']:  # TODO: Check type and name correspondance on real data
                    if sensor['data_type'] == "DT_mMeter" and mes['unit'] == 'mm':
                        return float(mes['value'])
                    elif sensor['data_type'] == "DT_mMeterHour" and mes['unit'] == 'mm/h':
                        return float(mes['value'])
            if sensor['reference'] == "low_battery" :
                return int(self.data['infos']['lowBatt'])
            elif sensor['reference'] == "rf_quality" :
                return int(self.data['header']['rfQuality']) * 10
        except :
            print(u"{0}".format(traceback.format_exc()))
            pass
        return None

    def get_Available_Sensors(self):
        """Return all dmg sensors id available by this infotype, for device detection"""
        return [["total_rain", "rain", "low_battery", "rf_quality"]]

class InfoType10(InfoType0) :
    """Info Type for X2D protocol"""

    infoType = "10"

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return ["8"]

    def get_RFP_data_to_sensor(self, data, data_type):
        """ Return sensor value from RFP data"""
        return None

class InfoType11(InfoType10) :
    """Info Type for X2D protocol"""

    infoType = "11"

    def get_RFP_data_to_sensor(self, data, data_type):
        """ Return sensor value from RFP data"""
        return None

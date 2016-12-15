#!/usr/bin/python
# -*- coding: utf-8 -*-

import traceback

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
    def isValid(self):
        """ Check coherente data protocol"""
        return  self.data['header']['protocol'] in self.protocols_Id

    def get_RFP_data_to_sensor(self, data_type, sensor=None):
        """Return sensor value from RFP data
            @param data_type : the domogik sensor data_type dict.
            @return : value in data_type format, else None.
        """
        return None

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

    def get_RFP_data_to_sensor(self, data_type, sensor=None):
        """Return sensor value from RFP data"""
        try :
            if (data_type == "DT_Bool") or ("parent" in data_type and data_type['parent'] == "DT_Bool"):
                return self.data['infos']['subType']
        except :
            pass
        return None

class InfoType1(InfoType0) :
    """Info Type for X10, BLYSS, CHACON, KD101 protocol"""

    infoType = "1"

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return ["1", "3", "4", "10"]

    def get_RFP_data_to_sensor(self, data, data_type):
        """Return sensor value from RFP data"""
        try :
            if (data_type == "DT_Bool") or ("parent" in data_type and data_type['parent'] == "DT_Bool"):
                return data['infos']['subType']
        except :
            pass
        return None

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

    def get_RFP_data_to_sensor(self, data, data_type, sensor=None):
        """Return sensor value from RFP data"""
        try :
            qualifier = int(data['infos']['qualifier'])
            if data['infos']['subType'] == "0" : # detector/sensor/ PowerCode device
                if (data_type == "DT_Bool") or ("parent" in data_type and data_type['parent'] == "DT_Bool"):
                    if sensor is not None :
                       # 1 : Down /OFF, 4 : My, 7 : Up / ON, 13 : ASSOC
                        if sensor['data_type'] in 'DT_UpDown' :
                            if qualifier == 1 : return "1"
                            if qualifier == 7 : return "0"
                        else :
                            if qualifier == 1 : return "0"
                            if qualifier == 7 : return "1"
                        if qualifier == 4 : return "1"
            elif data['infos']['subType'] == "1" : # remote control device (MCT-234 style)
                if (data_type == "DT_Bool") or ("parent" in data_type and data_type['parent'] == "DT_Bool"):
                    if sensor is not None :
                        # 5 : Left button 6 : Right button
                        if sensor['reference'] == 'button_1' :
                            return "1" if qualifier and 0x08 else "0"
                        elif sensor['reference'] == 'button_2' :
                            return "1" if qualifier and 0x10 else "0"
                        elif sensor['reference'] == 'button_3' :
                            return "1" if qualifier and 0x20 else "0"
                        elif sensor['reference'] == 'button_3' :
                            return "1" if qualifier and 0x40 else "0"
        except :
            pass
        return None

class InfoType3(InfoType0) :
    """Info Type for RTS protocol"""

    infoType = "3"

    @property
    def protocols_Id(self):
        """ Return protocols id compatibility"""
        return ["9"]

    def get_RFP_data_to_sensor(self, data, data_type, sensor=None):
        """Return sensor value from RFP data
            InfoType 3 used only for command
        """
        return None

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
            if sensor['reference'] == "battery_status" :
                return "0" if self.data['infos']['lowBatt'] == "1" else "1"
            elif sensor['reference'] == "rf_quality" :
                return int(self.data['header']['rfQuality']) * 10
        except :
            print(u"{0}".format(traceback.format_exc()))
            pass
        return None

class InfoType5(InfoType4) :
    """Info Type for OREGON protocol"""

    infoType = "5"

    def get_RFP_data_to_sensor(self, data, data_type):
        """ Return sensor value from RFP data"""
        return None

class InfoType6(InfoType4) :
    """Info Type for OREGON protocol"""

    infoType = "6"

    def get_RFP_data_to_sensor(self, data, data_type):
        """ Return sensor value from RFP data"""
        return None

class InfoType7(InfoType4) :
    """Info Type for OREGON protocol"""

    infoType = "7"

    def get_RFP_data_to_sensor(self, data, data_type):
        """ Return sensor value from RFP data"""
        return None

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

    def get_RFP_data_to_sensor(self, data, data_type):
        """ Return sensor value from RFP data"""
        return None

class InfoType9(InfoType4) :
    """Info Type for OREGON protocol"""

    infoType = "9"

    def get_RFP_data_to_sensor(self, data, data_type):
        """ Return sensor value from RFP data"""
        return None

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

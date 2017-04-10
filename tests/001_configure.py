#!/usr/bin/python

from domogik.tests.common.helpers import configure, delete_configuration
from domogik.common.utils import get_sanitized_hostname

name = "rfplayer"

print(delete_configuration("plugin", name, get_sanitized_hostname()))
print(u"Plugin {0} configuration deleted".format(name))
print(configure("plugin", name, get_sanitized_hostname(), "configured", True))
print(u"Plugin {0} configured".format(name))

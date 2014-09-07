import base64
import glob
import logging
import os

__author__ = 'edio'


def get_devpath(sysfs, devpath_relative):
    return sysfs + devpath_relative


def get_devname(devname_long):
    return os.path.basename(devname_long)


class SysfsDevice:
    def __init__(self, sysfsroot, devpath):
        self.devpath = get_devpath(sysfsroot, devpath)
        self.devname = get_devname(devpath)

    def get_active_connections(self):

        connections = []

        prefix = os.path.join(self.devpath, self.devname + '-')
        mask = prefix + "*"

        logging.debug("Searching outputs by mask: {0}".format(mask))

        for output in glob.glob(mask):
            with open(os.path.join(output, 'status')) as status_file:
                status = status_file.readline().strip()
            if status == 'connected':
                outName = output.replace(prefix, "", 1)
                with open(os.path.join(output, 'edid'), 'rb') as edid_file:
                    edid = edid_file.read()
                edidStr = base64.b64encode(edid)

                c = Connection(outName, edidStr)
                connections.append(c)

        return connections


class Connection:
    def __init__(self, output, edid: str=None):
        self.output = output
        self.edid = edid

    def __repr__(self):
        return "{0} [{1}...]".format(self.output, self.edid[0:12])

    def __eq__(self, obj):
        return isinstance(obj, Connection) and self.output.lower() == obj.output.lower() and self.edid == obj.edid

    def __hash__(self):
        return self.output.__hash__()

#!/usr/bin/env python
from pylibftdi import Device, FtdiError
from sys import stdout, exit
from os import system
from lib.UnbufferedStreamWrapper import *
from lib.Hexdump import *
import argparse
import abc


class RS485Monitor:
    __metaclass__ = abc.ABCMeta

    def __init__(self, single = 0, baudrate = 1250000, databits = 8, stopbits = 0, paritymode = 2):
        self._single = single
        self._count = 0
        self._out = UnbufferedStreamWrapper(stdout)
        try:
            self._d = Device()
            self._d.baudrate = baudrate
            self._d.ftdi_fn.ftdi_set_line_property(databits, stopbits, paritymode)
            self._d.flush()
        except FtdiError as e:
            print '\rCould not start FTDI Device : ' + e.args[0]
            exit(0)

    @abc.abstractmethod
    def run(self):
        return

class MonitorNormal(RS485Monitor):
    def __init__(self, *args, **kwargs):
        super(MonitorNormal, self).__init__(*args, **kwargs)

    def run(self):
        system('clear')
        self._out.write("Monitor started : Baudrate={0} [Normal mode]\n".format(self._d.baudrate))

        while (1):
            buf = self._d.read(256)
            self._out.write(buf)
            if (self._single and len(buf)):
                self._count += 1
            if (self._single and (self._count >= self._single)):
                raise KeyboardInterrupt

class MonitorHexdump(RS485Monitor):
    def __init__(self, *args, **kwargs):
        super(MonitorHexdump, self).__init__(*args, **kwargs)
        self._hexdump = Hexdump()

    def run(self):
        system('clear')
        self._out.write("Monitor started : Baudrate={0} [Hexdump mode]\n".format(self._d.baudrate))

        while (1):
            buf = self._d.read(256)
            self._hexdump.write(buf)
            if (self._single and len(buf)):
                self._count += 1
            if (self._single and (self._count >= self._single)):
                raise KeyboardInterrupt


class MonitorRaw(RS485Monitor):
    def __init__(self, *args, **kwargs):
        super(MonitorRaw, self).__init__(*args, **kwargs)

    def run(self):
        system('clear')
        self._out.write("Monitor started : Baudrate={0} [Raw mode]\n".format(self._d.baudrate))

        while (1):
            buf = self._d.read(2)
            if len(buf):
                for c in buf:
                    self._out.write(format(ord(c), 'x'))
                self._out.write(':')
            if (self._single and len(buf)):
                self._count += 1
            if (self._single and (self._count >= self._single)):
                raise KeyboardInterrupt



def main():
    classDict = {
        'normal'  : globals()['MonitorNormal'],
        'hexdump' : globals()['MonitorHexdump'],
        'raw'     : globals()['MonitorRaw']
    }
    p = argparse.ArgumentParser(prog='RS485Monitor.py', description='Monitor FTDI RS485 Rx.')
    p.add_argument('-m', '--mode',
                    choices=['normal', 'hexdump', 'raw'],
                    default = 'normal',
                    help='Raw output')
    p.add_argument('-s', '--single',
                    type = int,
                    default = 0,
                    help='Single shot mode')
    args = p.parse_args()
    mon = classDict[args.mode](args.single)

    try:
        mon.run()
    except FtdiError as e:
        print 'Exception caught : ' + e.args[0]
    except KeyboardInterrupt:
        pass

    print '\r\nExiting monitor'
    exit(0)

if __name__ == "__main__":
    main()

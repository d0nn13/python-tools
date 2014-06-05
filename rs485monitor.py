#!/usr/bin/env python
from pylibftdi import Device, FtdiError
from sys import stdout, exit
from os import system
import argparse

'''
Wraps a stream object into an auto-flushing one
'''
class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

class RS485Monitor:
    def __init__(self, baudrate = 1250000, databits = 8, stopbits = 0, paritymode = 2):
        try:
            self._d = Device()
        except FtdiError as e:
            print '\rCould not start FTDI Device : ' + e.args[0]
            exit(0)
        self._d.baudrate = baudrate
        self._d.ftdi_fn.ftdi_set_line_property(databits, stopbits, paritymode)
        self._d.flush()
        self._out = Unbuffered(stdout)
        self._raw = False

    def raw(self):
        self._out.write(self._d.read(1))

    def normal(self):
        d = self._d.read(128)
        self._out.write('\r')
        if (len(d) > 0):
            self._out.write('[' + d + '] (' + str(len(d)) + ')')

    def run(self):
        system('clear')
        self._out.write("Monitor started : Baudrate=" + str(self._d.baudrate))
        if (self._raw):
            self._out.write(' - [Raw mode]\n')
        else:
            self._out.write('\n[] (0)')

        while (1):
            try:
                if (self._raw):
                    self.raw()
                else:
                    self.normal()
            except FtdiError as e:
                print 'Exception caught : ' + e.args[0]
                print 'Exiting monitor'
                exit(1)
            except KeyboardInterrupt:
               print '\r\nExiting monitor'
               exit(0)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description='Monitor FTDI RS485 Rx.')
    p.add_argument('-r', '--raw',
                    default = False,
                    action="store_true",
                    help='Raw output')
    args = p.parse_args()
    mon = RS485Monitor()
    mon._raw = args.raw
    mon.run()

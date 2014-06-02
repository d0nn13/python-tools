#!/usr/bin/env python
from pylibftdi import Device, FtdiError
from sys import stdout, exit
from os import system

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

    def run(self):
        system('clear')
        print "Monitor started : Baudrate=" + str(self._d.baudrate)
        out = Unbuffered(stdout)
        d = ''
        for i in range(128):
            d += ' '

        while (1):
            try:
                d = self._d.read(128)
                for i in range (150):
                    out.write(' ')
                out.write('\r')
                out.write('[' + d + '] (' + str(len(d)) + ')\r')
            except FtdiError as e:
                print 'Exception caught : ' + e.args[0]
                print 'Exiting monitor'
                exit(1)
            except KeyboardInterrupt:
               print '\r\nExiting monitor'
               exit(0)

if __name__ == "__main__":
    mon = RS485Monitor()
    mon.run()

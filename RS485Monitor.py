#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created on 2014/05/05
Last Update on 2014/09/02

Author: Samir Ahamada
Contact: sahamada@aldebaran.com
"""

from lib.Output import UnbufferedStreamWrapper
from lib.Output import Hexdump
from pylibftdi import Device
from pylibftdi import FtdiError
from sys import stdout
from os import system, path
import abc
import argparse

normColor = '\x1b[0;0m'
lablColor = '\x1b[33m'
valuColor = '\x1b[1;37m'


class RS485MonitorException(Exception):
    def __init__(self, sender, msg):
        self.__sender = sender
        self.__msg = msg

    def __str__(self):
        return repr(self.__msg)


class RS485Monitor(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, a, mode='t', baudrate=1250000,
                 databits=8, stopbits=0, paritymode=2):
        self._single = a.single
        self._count = 0
        self._out = UnbufferedStreamWrapper(stdout)

        try:
            self._d = Device()
            self._d.baudrate = baudrate
            self._d.ftdi_fn.ftdi_set_line_property(databits,
                                                   stopbits,
                                                   paritymode)
            self._d.flush()
        except FtdiError as e:
            self._d = None
            raise FtdiError('could not start FTDI Device "' + e.args[0] + '"')

    def __del__(self):
        try:
            if self._d:
                self._d.flush()
                self._d.close()
        except:
            print 'Destroy failed'
        print normColor + '\nExiting monitor'

    @abc.abstractmethod
    def run(self):
        pass


class MonitorNormal(RS485Monitor):
    def __init__(self, a, *args, **kwargs):
        super(MonitorNormal, self).__init__(a, *args, **kwargs)

    def run(self):
        system('clear')
        self._out.write('Monitor started : ')
        self._out.writeln('Baudrate=' + str(self._d.baudrate) +
                          ' [Normal mode]')

        while (1):
            buf = self._d.read(256)
            self._out.write(buf)
            if (self._single and len(buf)):
                self.__count += 1
            if (self._single and (self.__count >= self._single)):
                raise KeyboardInterrupt


class MonitorHexdump(RS485Monitor):
    def __init__(self, a, *args, **kwargs):
        super(MonitorHexdump, self).__init__(a, *args, **kwargs)
        self.__hexdump = Hexdump()

    def run(self):
        system('clear')
        self._out.write('Monitor started : ')
        self._out.writeln('Baudrate=' + str(self._d.baudrate) +
                          ' [Hexdump mode]')

        while (1):
            buf = self._d.read(256)
            self.__hexdump.write(buf)
            if (self._single and len(buf)):
                self.__count += 1
            if (self._single and (self.__count >= self._single)):
                raise KeyboardInterrupt


class MonitorRaw(RS485Monitor):
    def __init__(self, a, *args, **kwargs):
        super(MonitorRaw, self).__init__(a, *args, **kwargs)

    def run(self):
        system('clear')
        self._out.write('Monitor started : ')
        self._out.writeln('Baudrate=' + str(self._d.baudrate) + ' [Raw mode]')

        while (1):
            buf = self._d.read(2)
            if len(buf):
                for c in buf:
                    self._out.write(format(ord(c), 'x'))
                self._out.write(':')
            if (self._single and len(buf)):
                self.__count += 1
            if (self._single and (self.__count >= self._single)):
                raise KeyboardInterrupt


def main():
    classDict = {
        'normal': globals()['MonitorNormal'],
        'hexdump': globals()['MonitorHexdump'],
        'raw': globals()['MonitorRaw']
    }
    p = argparse.ArgumentParser(prog='RS485Monitor.py',
                                description='Monitor FTDI RS485 Rx.')
    p.add_argument('--mode', '-m',
                   choices=['normal', 'hexdump', 'raw'],
                   default='normal',
                   help='Monitor mode')

    p.add_argument('--single', '-s',
                   type=int,
                   default=0,
                   metavar='N',
                   help='Single shot mode: stops after printing N lines')

    p.add_argument('--log', '-l',
                   type=str,
                   default='',
                   metavar='FILE',
                   help='(dts) Log file output: Print log into FILE')

    p.add_argument('--no-stdout',
                   default=False,
                   action='store_true',
                   help='(dts) Disable stdout printing')

    p.add_argument('--newline', '-r',
                   default=False,
                   action='store_true',
                   help='(dts) One line monitoring')

    args = p.parse_args()

    try:
        mon = classDict[args.mode](args)
        mon.run()
    except FtdiError as e:
        print normColor + 'FTDI Exception caught : ' + e.args[0]
    except RS485MonitorException as e:
        print normColor + '[{0}] : {1}'.format(e.sender, e.msg)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

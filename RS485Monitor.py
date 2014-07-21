#!/usr/bin/env python
from lib.UnbufferedStreamWrapper import UnbufferedStreamWrapper
from lib.Hexdump import Hexdump
from pylibftdi import Device, FtdiError
from sys import stdout, exit
from os import system
from time import sleep
from struct import unpack
import abc
import argparse
import json

normColor = '\x1b[0;0m'
lablColor = '\x1b[33m'
valuColor = '\x1b[1;37m'


class RS485MonitorException(Exception):
    def __init__(self, sender, msg):
        self.sender = sender
        self.msg = msg

    def __str__(self):
        return repr(self.value)


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
            raise FtdiError('could not start FTDI Device "' + e.args[0] + '"')

    @abc.abstractmethod
    def run(self):
        return


class MonitorNormal(RS485Monitor):
    def __init__(self, a, *args, **kwargs):
        super(MonitorNormal, self).__init__(a, *args, **kwargs)

    def run(self):
        system('clear')
        self._out.write('Monitor started : ')
        self._out.writeln('Baudrate=' + self._d.baudrate + ' [Normal mode]')

        while (1):
            buf = self._d.read(256)
            self._out.write(buf)
            if (self._single and len(buf)):
                self._count += 1
            if (self._single and (self._count >= self._single)):
                raise KeyboardInterrupt


class MonitorHexdump(RS485Monitor):
    def __init__(self, a, *args, **kwargs):
        super(MonitorHexdump, self).__init__(a, *args, **kwargs)
        self._hexdump = Hexdump()

    def run(self):
        system('clear')
        self._out.write('Monitor started : ')
        self._out.writeln('Baudrate=' + self._d.baudrate + ' [Hexdump mode]')

        while (1):
            buf = self._d.read(256)
            self._hexdump.write(buf)
            if (self._single and len(buf)):
                self._count += 1
            if (self._single and (self._count >= self._single)):
                raise KeyboardInterrupt


class MonitorRaw(RS485Monitor):
    def __init__(self, a, *args, **kwargs):
        super(MonitorRaw, self).__init__(a, *args, **kwargs)

    def run(self):
        system('clear')
        self._out.write('Monitor started : ')
        self._out.writeln('Baudrate=' + self._d.baudrate + ' [Raw mode]')

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


class MonitorDTS(RS485Monitor):
    def __init__(self, a, *args, **kwargs):
        super(MonitorDTS, self).__init__(a, *args, **kwargs)
        self._hexdump = Hexdump()
        self._endianKeys = {'B': '>', 'L': '<'}
        self._typeKeys = {'h': 2, 'H': 2, 'i': 4, 'I': 4,
                          'q': 8, 'Q': 8, 'f': 4, 'd': 8, 'x': 1}
        self._sof = ['\x73', '\x95', '\xDB', '\x42']

        self._buffer = []
        self._frameDesc = {}
        self._decoder = ''
        self._labels = []
        self._frameDescFile = a.desc
        self._logFile = a.log
        self._displayFrameNb = a.frame_number
        self._dataSize = 0
        self._sofok = 0
        self._start = 0
        self._frameNb = 0
        self._firstWrite = 1

    def _loadFrameDesc(self):
        with open(self._frameDescFile) as f:
            try:
                self._frameDesc = json.loads(f.read())
            except ValueError as e:
                raise RS485MonitorException('loadFrameDesc:json.loads',
                                            e.args[0])

        if not type(self._frameDesc) == dict or \
            not len(self._frameDesc) == 2 or \
                not 'endianess' in self._frameDesc.keys() or \
                    not 'items' in self._frameDesc.keys():
            raise RS485MonitorException('loadFrameDesc',
                                        'Invalid frame descriptor')

        if not self._frameDesc['endianess'] in self._endianKeys:
            raise RS485MonitorException('loadFrameDesc',
                                        'Unrecognized endianess')
        self._decoder = self._endianKeys[self._frameDesc['endianess']]

        if type(self._frameDesc['items']) != list:
            raise RS485MonitorException('loadFrameDesc',
                                        'Unrecognized item list format')

        for item in self._frameDesc['items']:
            if type(item) != dict or \
                    len(item.values()) != 1 or len(item.keys()) != 1:
                raise RS485MonitorException('loadFrameDesc',
                                            'Unrecognized item size')

            if not item.values()[0] in self._typeKeys:
                raise RS485MonitorException('loadFrameDesc',
                                            'Unrecognized item type')

            self._decoder += item.values()[0].encode('ascii')
            self._dataSize += self._typeKeys[item.values()[0]]
            if (item.values()[0] != 'x'):
                self._labels.append(item.keys()[0].encode('ascii'))

        if self._dataSize % 2:
            raise RS485MonitorException('loadFrameDesc',
                                        'Data size is not even')

    def _readBuffer(self):
        while len(self._buffer) < (self._dataSize + len(self._sof)):
            buf = self._d.read(256)
            '''
            buf = ''.join(self._sof) + '\x10\x00\x10\x00\x20\x00\x00\x00'
            buf += '\x00\x00\x80\x41\x00\x00\x00\x00\x00\x00\x40\x40'
            sleep(.03)
            '''
            for c in buf:
                if len(c):
                    self._buffer.append(c)

    def _getSOF(self):
        if (self._sofok >= len(self._sof)):
            if len(self._buffer) < (self._dataSize + len(self._sof)):
                self._readBuffer()
            self._sofok = 0
            self._start = 1
            return

        if (self._start or len(self._buffer) < 4):
            self._readBuffer()
        if (self._buffer.pop(0) == self._sof[self._sofok]):
            self._sofok += 1
        else:
            self._sofok = 0
            self._getSOF()

    def _decodeFrame(self, frame):
        if len(frame) != self._dataSize:
            err = 'FATAL: Got ' + len(frame) + 'bytes instead of '
            err += self._dataSize + '. Check JSON config file and/or FW!'
            raise RS485MonitorException('decodeFrame', err)
        values = unpack(self._decoder, frame)
        return ([self._labels, values])

    def _printData(self, data):
        self._out.write('| ')
        for i in range(len(data[0])):
            out = '{lC}[{l}]{lc}: {vC}{v:>15}{vc} | '.format(lC=lablColor,
                                                             l=data[0][i],
                                                             lc=normColor,
                                                             vC=valuColor,
                                                             v=data[1][i],
                                                             vc=normColor)
            self._out.write(out)
        if self._displayFrameNb:
            self._out.write('{} '.format(self._frameNb))
        self._out.write('\n')

    def _writeFile(self, data):
        values = []

        if self._firstWrite:
            self._firstWrite = 0
            with open(self._logFile, 'w') as f:
                f.write('# ' + ', '.join(data[0]) + '\n')
        else:
            for v in data[1]:
                values.append(str(v))
            with open(self._logFile, 'a') as f:
                f.write('  ' + ', '.join(values) + '\n')

    def run(self):
        self._loadFrameDesc()
        system('clear')
        self._out.write('Monitor started : ')
        self._out.write('Baudrate=' + str(self._d.baudrate) + '[DTS mode]\t')
        self._out.writeln('<Datasize: {0} bytes>'.format(self._dataSize))

        while (1):
            self._readBuffer()
            if not self._start:
                self._getSOF()
            c = 0
            frame = ''
            while (self._start):
                frame += self._buffer.pop(0)
                c += 1
                if (c < self._dataSize):
                    continue
                self._frameNb += 1
                self._start = 0
                data = self._decodeFrame(frame)
                self._printData(data)
                if len(self._logFile):
                    self._writeFile(data)


def main():
    classDict = {
        'normal': globals()['MonitorNormal'],
        'hexdump': globals()['MonitorHexdump'],
        'raw': globals()['MonitorRaw'],
        'dts': globals()['MonitorDTS']
    }
    p = argparse.ArgumentParser(prog='RS485Monitor.py',
                                description='Monitor FTDI RS485 Rx.')
    p.add_argument('-m', '--mode',
                   choices=['normal', 'hexdump', 'raw', 'dts'],
                   default='normal',
                   help='Monitor mode')
    p.add_argument('-s', '--single',
                   type=int,
                   default=0,
                   help='Single shot mode')
    p.add_argument('-d', '--desc',
                   type=str,
                   default='dtsframe.json',
                   help='Frame Descriptor (DTS)')
    p.add_argument('-l', '--log',
                   type=str,
                   default='',
                   help='Log file output (DTS)')
    p.add_argument('-n', '--frame-number',
                   default=False,
                   action='store_true',
                   help='Print frame Number (DTS)')

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

    print normColor + '\r\nExiting monitor'

if __name__ == "__main__":
    main()

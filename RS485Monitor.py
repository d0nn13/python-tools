#!/usr/bin/env python
from lib.UnbufferedStreamWrapper import UnbufferedStreamWrapper
from lib.Hexdump import Hexdump
from pylibftdi import Device, FtdiError
from sys import stdout
from os import system, path
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
        return repr(self.msg)


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

    def __del__(self):
        try:
            self._d.flush()
        except:
            print 'Destroy failed'
        try:
            self._d.close()
        except:
            print 'Destroy failed'
        print normColor + '\nExiting monitor'

    @abc.abstractmethod
    def run(self):
        return


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
        self._out.writeln('Baudrate=' + str(self._d.baudrate) +
                          ' [Hexdump mode]')

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
        self._out.writeln('Baudrate=' + str(self._d.baudrate) + ' [Raw mode]')

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
        self._structDesc = {}
        self._decoder = ''
        self._labels = []
        self._structDescFile = a.desc
        self._logFile = a.log
        self._logIO = None
        self._noStdoutPrint = a.no_stdout
        self._displayFrameNb = a.frame_number
        self._dataSize = 0
        self._sofok = 0
        self._start = 0
        self._frameNb = 0

        if a.no_stdout and not len(a.log):
            raise RS485MonitorException(
                'init', 'Neither file logging or stdout printing enabled')

    def __del__(self):
        if len(self._logFile) and not self._logIO.closed:
            print '\nClosing log file'
            self._logIO.close()
        super(MonitorDTS, self).__del__()

    def _initDts(self):
        self._loadStructDesc()
        if len(self._logFile):
            self._initLogFile()
        system('clear')
        self._out.write('Monitor started : ')
        self._out.write('Baudrate=' + str(self._d.baudrate) + ' [DTS mode]\t')
        self._out.writeln('<Datasize: {0} bytes>'.format(self._dataSize))
        self._out.writeln('Using struct descriptor file : \'' +
                          self._structDescFile + '\'')
        if self._noStdoutPrint:
            self._out.writeln('Stdout printing disabled')
        if isinstance(self._logIO, file):
            self._out.writeln('Logging to file: \'' + self._logFile + '\'')

    def _loadStructDesc(self):
        with open(self._structDescFile) as f:
            try:
                self._structDesc = json.loads(f.read())
            except ValueError as e:
                raise RS485MonitorException('loadStructDesc:json.loads',
                                            e.args[0])

        if not type(self._structDesc) == dict or \
            not len(self._structDesc) == 2 or \
                'endianess' not in self._structDesc.keys() or \
                'items' not in self._structDesc.keys():
            raise RS485MonitorException('loadFrameDesc',
                                        'Invalid frame descriptor')

        if not self._structDesc['endianess'] in self._endianKeys:
            raise RS485MonitorException('loadFrameDesc',
                                        'Unrecognized endianess')
        self._decoder = self._endianKeys[self._structDesc['endianess']]

        if type(self._structDesc['items']) != list:
            raise RS485MonitorException('loadFrameDesc',
                                        'Unrecognized item list format')

        for item in self._structDesc['items']:
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

    def _initLogFile(self):
        mode = 'a' if path.exists(self._logFile) else 'w'
        self._logIO = open(self._logFile, mode, 1)
        if not isinstance(self._logIO, file) or \
            not mode == self._logIO.mode or \
                self._logIO.closed:
            raise RS485MonitorException('initLogFile', 'Couldn\'t open file')

        if mode == 'a':
            self._logIO.write('\n\n\n')
            for i in range(79):
                self._logIO.write('#')
            self._logIO.write('\n')
        self._logIO.write(
            '# Using struct descriptor: \'' + self._structDescFile + '\'\n')
        self._logIO.write('# Frame, ' + ', '.join(self._labels) + '\n')

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
        while (not self._start):
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

    def _decodeFrame(self, frame):
        if len(frame) != self._dataSize:
            err = 'FATAL: Got ' + str(len(frame)) + ' bytes instead of '
            err += str(self._dataSize) + '. Check JSON config file and/or FW!'
            raise RS485MonitorException('decodeFrame', err)
        values = unpack(self._decoder, frame)
        return ([self._labels, values])

    def _printDataToTerm(self, data):
        self._out.write('| ')
        for i in range(len(data[0])):
            out = '{lC}[{l}]{lc}: {vC}{v:>19}{vc} | '.format(lC=lablColor,
                                                             l=data[0][i],
                                                             lc=normColor,
                                                             vC=valuColor,
                                                             v=data[1][i],
                                                             vc=normColor)
            self._out.write(out)
        if self._displayFrameNb:
            self._out.write('{} '.format(self._frameNb))
        self._out.write('\n')

    def _printDataToFile(self, data):
        values = []

        for v in data[1]:
            values.append(str(v))
        self._logIO.write('  ' + str(self._frameNb) + ', ' + ', '.join(values))
        self._logIO.write('\n')

    def run(self):
        self._initDts()
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
                if not self._noStdoutPrint:
                    self._printDataToTerm(data)
                if len(self._logFile):
                    self._printDataToFile(data)


def main():
    classDict = {
        'normal': globals()['MonitorNormal'],
        'hexdump': globals()['MonitorHexdump'],
        'raw': globals()['MonitorRaw'],
        'dts': globals()['MonitorDTS']
    }
    p = argparse.ArgumentParser(prog='RS485Monitor.py',
                                description='Monitor FTDI RS485 Rx.')
    p.add_argument('--mode', '-m',
                   choices=['normal', 'hexdump', 'raw', 'dts'],
                   default='normal',
                   help='Monitor mode')

    p.add_argument('--single', '-s',
                   type=int,
                   default=0,
                   metavar='N',
                   help='Single shot mode: stops after printing N lines')

    p.add_argument('--desc', '-d',
                   type=str,
                   default='defaultstruct.json',
                   metavar='FILE',
                   help='(dts) Struct Descriptor: \
                       Use FILE as struct descriptor')

    p.add_argument('--log', '-l',
                   type=str,
                   default='',
                   metavar='FILE',
                   help='(dts) Log file output: Print log into FILE')

    p.add_argument('--no-stdout',
                   default=False,
                   action='store_true',
                   help='(dts) Disable stdout printing')

    p.add_argument('--frame-number', '-n',
                   default=False,
                   action='store_true',
                   help='(dts) Print frame Number')

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

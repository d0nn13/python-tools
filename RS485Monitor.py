#!/usr/bin/env python
from pylibftdi import Device, FtdiError
from sys import stdout, exit
from os import system
from time import sleep
from binascii import b2a_hex
from struct import unpack
from lib.UnbufferedStreamWrapper import *
from lib.Hexdump import *
import argparse, abc, json

class RS485MonitorException(Exception):
    pass


class RS485Monitor(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, single = 0, mode='t', baudrate = 1250000, databits = 8, stopbits = 0, paritymode = 2):
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
            exit(1)

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


class MonitorDTS(RS485Monitor):
    def __init__(self, *args, **kwargs):
        super(MonitorDTS, self).__init__(*args, **kwargs)
        self._hexdump = Hexdump()
        self._endianesses = {'big' : '>', 'lil' : '<'}
        self._typeSizes = {'h' : 2, 'H' : 2, 'i' : 4, 'I' : 4,
                         'q' : 8, 'Q' : 8, 'f' : 4, 'd' : 8}
        self._sof = ['\x73', '\x95', '\xDB', '\x42']

        self._buffer = []
        self._config = []
        self._dataSize = 0
        self._sofok = 0
        self._start = 0
        self._frameNb = 0

        self.displayFrameNb = 0
        self.endianess = 'big'

    def _loadConfig(self):
        with open('dtsconfig.json') as f:
            try:
                self._config = json.loads(f.read())
            except ValueError as e:
                raise RS485MonitorException('json.loads', e.args[0])
        if not len(self._config):
            raise RS485MonitorException('loadConfig', 'Empty config file')
        for i in self._config:
            if len(i.values()) != 1 or len(i.keys()) != 1:
                raise RS485MonitorException('loadConfig', 'Invalid config file')
            if not i.values()[0] in self._typeSizes:
                raise RS485MonitorException('loadConfig', 'Invalid type in config file')
            self._dataSize += self._typeSizes[i.values()[0]]

    def _readBuffer(self):
        if len(self._buffer) >= (self._dataSize + len(self._sof)):
            return
        else:
            buf = self._d.read(256)
            for c in buf:
                if len(c):
                    self._buffer.append(c)
        self._readBuffer()

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
        buf = ''
        data = []
        off = 0

        if len(frame) != self._dataSize:
            err = 'Got {0} bytes instead of {1}.'.format(len(frame), self._dataSize)
            err += ' Check JSON config file and/or FW!'
            raise RS485MonitorException('decodeFrame', err)


        for obj in self._config:
            label = obj.keys()[0]
            if len(label):
                size = self._typeSizes[obj.values()[0]]
                for c in range(off, off + size):
                    buf = ''.join([frame[c], buf])
                buf = '{:\x00>4}'.format(buf)
                off += size
                dataType = '{endianess}{type}'.format(
                            endianess = self._endianesses[self.endianess],
                            type = obj.values()[0])
                data.append({label : unpack(dataType, buf)[0]})
                buf = ''

        return (data)

    def _printData(self, data):
        normColor = '\x1b[0;0m'
        lablColor = '\x1b[33m'
        valuColor = '\x1b[1;37m'

        if self.displayFrameNb:
            self._out.write('{:>10} '.format(self._frameNb))
        self._out.write('| ')
        for d in data:
            if len(d.values()) != 1 or len(d.keys()) != 1:
                raise RS485MonitorException('printData', 'Invalid data')
            string = '{lC}[{l}]{lc}: {vC}{v:>11}{vc} | '.format(
                    lC = lablColor,
                    l = d.keys()[0],
                    lc = normColor,
                    vC = valuColor,
                    v = d.values()[0],
                    vc = normColor)
            self._out.write(string)
        self._out.write('\n')


    def run(self):
        system('clear')
        self._loadConfig()
        self._out.write("Monitor started : Baudrate={0} [DTS mode]".format(self._d.baudrate))
        self._out.writeln("\t<Datasize: {0} bytes>".format(str(self._dataSize)))

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


def main():
    classDict = {
        'normal'  : globals()['MonitorNormal'],
        'hexdump' : globals()['MonitorHexdump'],
        'raw'     : globals()['MonitorRaw'],
        'dts'     : globals()['MonitorDTS']
    }
    p = argparse.ArgumentParser(prog='RS485Monitor.py', description='Monitor FTDI RS485 Rx.')
    p.add_argument('-m', '--mode',
                    choices=['normal', 'hexdump', 'raw', 'dts'],
                    default = 'normal',
                    help='Monitor mode')
    p.add_argument('-s', '--single',
                    type = int,
                    default = 0,
                    help='Single shot mode')
    args = p.parse_args()
    try:
        mon = classDict[args.mode](args.single)
        mon.run()
    except FtdiError as e:
        print 'FTDI Exception caught : ' + e.args[0]
    except RS485MonitorException as e:
        print '[{0}] : {1}'.format(e.args[0], e.args[1])
    except KeyboardInterrupt:
        pass

    print '\r\nExiting monitor'

if __name__ == "__main__":
    main()

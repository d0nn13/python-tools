#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created on 2014/05/05
Last Update on 2014/09/17

Author: Samir Ahamada
Contact: sahamada@aldebaran.com
"""
from lib.Output import UnbufferedStreamWrapper
from pylibftdi import Device
from pylibftdi import FtdiError
from sys import stdout
from os import system, path
from time import sleep
from struct import unpack
import argparse
import json

normColor = '\x1b[0;0m'
lablColor = '\x1b[33m'
valuColor = '\x1b[1;37m'


class DTSAnalyzerException(Exception):
    def __init__(self, sender, msg):
        self.sender = sender
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class DTSAnalyzer(object):
    def __init__(self, a, mode='t', baudrate=1250000,
                 databits=8, stopbits=0, paritymode=2):

        self.__endianKeys = {'B': '>', 'L': '<'}
        self.__typeKeys = {
            "sInt16": {"key": 'h', "size": 2},
            "uInt16": {"key": 'H', "size": 2},
            "sInt32": {"key": 'i', "size": 4},
            "uInt32": {"key": 'I', "size": 4},
            "sInt64": {"key": 'q', "size": 8},
            "uInt64": {"key": 'Q', "size": 8},
            "float": {"key": 'f', "size": 4},
            "double": {"key": 'd', "size": 8},
            "byte": {"key": 'x', "size": 1}
            }
        self.__sof = ['\x73', '\x95', '\xDB', '\x42']
        self.__structDescFile = a.desc
        self.__logFile = a.log
        self.__noStdoutPrint = a.no_stdout
        self.__displayFrameNb = a.frame_number
        self.__lineSep = '\n' if a.newline else '\r'
        self.__logIO = None
        self.__labels = []
        self.__buffer = []
        self.__structDesc = {}
        self.__decoder = ''
        self.__dataSize = 0
        self.__sofok = 0
        self.__start = 0
        self.__frameNb = 0

        self.__out = UnbufferedStreamWrapper(stdout)
        try:
            self.__d = Device()
            self.__d.baudrate = baudrate
            self.__d.ftdi_fn.ftdi_set_line_property(databits,
                                                    stopbits,
                                                    paritymode)
            self.__d.flush()
        except FtdiError as e:
            self.__d = None
            raise FtdiError('could not start FTDI Device "' + e.args[0] + '"')

        if a.no_stdout and not len(a.log):
            raise DTSAnalyzerException(
                'init', 'Neither file logging or stdout printing enabled')

        self.__initDts()

    def __del__(self):
        if self.__logIO and not self.__logIO.closed:
            print '\nClosing log file'
            self.__logIO.close()
        if self.__d:
            self.__d.flush()
            self.__d.close()
        print normColor + '\nExiting monitor'

    def __initDts(self):
        self.__loadStructDesc()
        if len(self.__logFile):
            self.__initLogFile()
        system('clear')
        self.__out.write('Analyzer started : ')
        self.__out.write('Baudrate=' + str(self.__d.baudrate) + '\t')
        self.__out.writeln('<Datasize: {0} bytes>'.format(self.__dataSize))
        self.__out.writeln('Using struct descriptor file : \'' +
                           self.__structDescFile + '\'')
        if self.__noStdoutPrint:
            self.__out.writeln('Stdout printing disabled')
        if isinstance(self.__logIO, file):
            self.__out.writeln('Logging to file: \'' + self.__logFile + '\'')

    def __loadStructDesc(self):
        with open(self.__structDescFile) as f:
            try:
                self.__structDesc = json.loads(f.read())
            except ValueError as e:
                raise DTSAnalyzerException('loadStructDesc:json.loads',
                                           e.args[0])

        if not type(self.__structDesc) == dict or \
            not len(self.__structDesc) == 2 or \
                'endianess' not in self.__structDesc.keys() or \
                'items' not in self.__structDesc.keys():
            raise DTSAnalyzerException('loadFrameDesc',
                                       'Invalid frame descriptor')

        if not self.__structDesc['endianess'] in self.__endianKeys:
            raise DTSAnalyzerException('loadFrameDesc',
                                       'Unrecognized endianess')
        self.__decoder = self.__endianKeys[self.__structDesc['endianess']]

        if type(self.__structDesc['items']) != list:
            raise DTSAnalyzerException('loadFrameDesc',
                                       'Unrecognized item list format')

        for item in self.__structDesc['items']:
            if type(item) != dict or \
                    len(item.values()) != 1 or len(item.keys()) != 1:
                raise DTSAnalyzerException('loadFrameDesc',
                                           'Unrecognized item size')

            if not item.values()[0] in self.__typeKeys:
                raise DTSAnalyzerException('loadFrameDesc',
                                           'Unrecognized item type')

            typeStr = item.values()[0].encode('ascii')
            self.__decoder += self.__typeKeys[typeStr]["key"]
            self.__dataSize += self.__typeKeys[typeStr]["size"]
            if (item.values()[0] != "byte"):
                self.__labels.append(item.keys()[0].encode('ascii'))

        if self.__dataSize % 2:
            raise DTSAnalyzerException('loadFrameDesc',
                                       'Data size is not even')

    def __initLogFile(self):
        mode = 'a' if path.exists(self.__logFile) else 'w'
        self.__logIO = open(self.__logFile, mode, 1)
        if not isinstance(self.__logIO, file) or \
            not mode == self.__logIO.mode or \
                self.__logIO.closed:
            raise DTSAnalyzerException('initLogFile', 'Couldn\'t open file')

        if mode == 'a':
            self.__logIO.write('\n\n\n')
            for i in range(79):
                self.__logIO.write('#')
            self.__logIO.write('\n')
        self.__logIO.write(
            '# Log generated with DTS logger and using struct descriptor: \'' +
            self.__structDescFile + '\'\n')
        self.__logIO.write('Frame,' + ','.join(self.__labels) + '\n')

    def __readBuffer(self):
        while len(self.__buffer) < (self.__dataSize + len(self.__sof)):
            buf = self.__d.read(256)
            '''
            buf = ''.join(self.__sof) + '\x10\x00\x10\x00\x20\x00\x00\x00'
            buf += '\x00\x00\x80\x41\x00\x00\x00\x00\x00\x00\x40\x40'
            sleep(.03)
            '''
            for c in buf:
                if len(c):
                    self.__buffer.append(c)

    def __getSOF(self):
        while (not self.__start):
            if (self.__sofok >= len(self.__sof)):
                if len(self.__buffer) < (self.__dataSize + len(self.__sof)):
                    self.__readBuffer()
                self.__sofok = 0
                self.__start = 1
                return

            if (self.__start or len(self.__buffer) < 4):
                self.__readBuffer()
            if (self.__buffer.pop(0) == self.__sof[self.__sofok]):
                self.__sofok += 1
            else:
                self.__sofok = 0

    def __checkCRC(self, frame, size, crcIn):
        crcOut = 0
        c = 0
        if len(frame[4:]) != self.__dataSize:
            err = 'FATAL: Got ' + str(len(frame[4:])) + ' bytes instead of '
            err += str(self.__dataSize) + '. Check JSON config file and/or FW!'
            raise DTSAnalyzerException('decodeFrame', err)
        for j in range(size):
            crcOut ^= ord(frame[c]) << 8
            for i in range(8):
                if (crcOut & 0x8000):
                    crcOut ^= (0x1070 << 3)
                crcOut <<= 1
            c += 1
        return ((crcOut >> 8) == ord(crcIn))

    def __decodeFrame(self, frame):
        values = unpack(self.__decoder, frame)
        return ([self.__labels, values])

    def __printDataToTerm(self, data):
        self.__out.write('| ')
        for i in range(len(data[0])):
            out = '{lC}[{l}]{lc}: {vC}{v:>19}{vc} | '.format(lC=lablColor,
                                                             l=data[0][i],
                                                             lc=normColor,
                                                             vC=valuColor,
                                                             v=data[1][i],
                                                             vc=normColor)
            self.__out.write(out)
        if self.__displayFrameNb:
            self.__out.write('{} '.format(self.__frameNb))
        self.__out.write(self.__lineSep)

    def __printDataToFile(self, data):
        values = []

        for v in data[1]:
            values.append(str(v))
        self.__logIO.write(str(self.__frameNb) + ',' + ','.join(values) + '\n')

    def run(self):
        crcFailNb = 0
        while (1):
            self.__readBuffer()
            if not self.__start:
                self.__getSOF()
            c = 0
            frame = "".join(self.__sof)
            while (self.__start):
                frame += self.__buffer.pop(0)
                c += 1
                if (c < self.__dataSize):
                    continue
                crc = self.__buffer.pop(0)
                self.__frameNb += 1
                self.__start = 0
                if not self.__checkCRC(frame, len(frame), crc):
                    crcFailNb += 1;
                    if (crcFailNb >= 10):
                        raise DTSAnalyzerException("run",
                                                   "Too much CRC errors")
                data = self.__decodeFrame(frame[4:])
                if not self.__noStdoutPrint:
                    self.__printDataToTerm(data)
                if len(self.__logFile):
                    self.__printDataToFile(data)


def main():
    descStr = 'Analyze data received via DTS (RS485).'
    p = argparse.ArgumentParser(prog='DTSAnalyzer.py',
                                description=descStr)
    p.add_argument('--desc', '-d',
                   type=str,
                   default='descriptor-examples/defaultstruct.json',
                   metavar='FILE',
                   help='(dts) Struct Descriptor: \
                       Use FILE as struct descriptor')

    p.add_argument('--log', '-l',
                   type=str,
                   default='',
                   metavar='FILE',
                   help='Log file output: Print log into FILE')

    p.add_argument('--no-stdout',
                   default=False,
                   action='store_true',
                   help='Disable stdout printing')

    p.add_argument('--frame-number', '-n',
                   default=False,
                   action='store_true',
                   help='Print frame Number')

    p.add_argument('--newline', '-r',
                   default=False,
                   action='store_true',
                   help='Multi-line monitoring')

    args = p.parse_args()

    try:
        dtsAnalyzer = DTSAnalyzer(args)
        dtsAnalyzer.run()
    except FtdiError as e:
        print normColor + 'FTDI Exception caught : ' + e.args[0]
    except DTSAnalyzerException as e:
        print normColor + '[{0}] : {1}'.format(e.sender, e.msg)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

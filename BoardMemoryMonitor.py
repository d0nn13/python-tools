#!/usr/bin/env python
from naoqi import ALBroker, ALProxy
from sys import stdout, exit
from os import system
from re import compile, search
from UnbufferedStreamWrapper import *
import argparse


class BoardMemoryMonitor:
    def __init__(self, args):
        try:
            self._mem = ALProxy('ALMemory', args.url, args.port)
            self._out = UnbufferedStreamWrapper(stdout)
            self._prefix = 'Device/DeviceList'
            self._board = args.board
            self._key = args.key
        except RuntimeError as e:
            exceptRgx = compile('[^\n\t]+$')
            print '\n', 'RuntimeError:', exceptRgx.search(e.args[0]).group(0)
            exit(1)
        except Exception as e:
            print e
            exit(1)


    def run(self):
        try:
            progVersion = self._mem.getData('/'.join([self._prefix,
                                                    self._board,
                                                    'ProgVersion']))
            system('clear')
            print 'Monitoring key \'{0}\' on board \'{1}\' [ProgVersion: {2}]'.format(self._key,
                                                                                    self._board,
                                                                                    str(progVersion))
            while True:
                data = self._mem.getData('/'.join([self._prefix, self._board, self._key]))
                self._out.write(str(data))
                self._out.write('   \r')
        except KeyboardInterrupt:
            print '\r\nExiting monitor'
            exit(0)
        except RuntimeError as e:
            exceptRgx = compile('[^\n\t]+$')
            print '\n', 'RuntimeError:', exceptRgx.search(e.args[0]).group(0)
            exit(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description='Monitor errors on specific board')
    p.add_argument('-u', '--url',
                    default = 'bn9.local')
    p.add_argument('-p', '--port',
                    default = 9559)
    p.add_argument('-b', '--board',
                    default = 'ZeBoard')
    p.add_argument('-k', '--key',
                    default = 'Error')
    args = p.parse_args()
    mon = BoardMemoryMonitor(args)
    mon.run()

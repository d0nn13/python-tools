#!/usr/bin/env python
from naoqi import ALBroker, ALProxy
from sys import stdout, exit
from os import system
from re import compile, search
from lib.UnbufferedStreamWrapper import *
import argparse


class BoardMemoryMonitor(object):
    def __init__(self, args):
        self._prefix = 'Device/DeviceList'
        self._board = args.board
        self._key = args.key
        try:
            self._mem = ALProxy('ALMemory', args.url, args.port)
            self._out = UnbufferedStreamWrapper(stdout)
        except RuntimeError as e:
            exceptRgx = compile('[^\n\t]+$')
            print '\n', 'RuntimeError:', exceptRgx.search(e.args[0]).group(0)
            exit(1)

    def run(self):
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


def main():
    p = argparse.ArgumentParser(description='Monitor errors on specific board')
    p.add_argument('-u', '--url',
                   default='bn9.local')
    p.add_argument('-p', '--port',
                   default=9559)
    p.add_argument('-b', '--board',
                   default='ZeBoard')
    p.add_argument('-k', '--key',
                   default='Error')
    args = p.parse_args()
    mon = BoardMemoryMonitor(args)

    try:
        mon.run()
    except RuntimeError as e:
        exceptRgx = compile('[^\n\t]+$')
        print '\n', 'RuntimeError:', exceptRgx.search(e.args[0]).group(0)
        exit(1)
    except KeyboardInterrupt:
        pass

    print '\r\nExiting monitor'

if __name__ == "__main__":
    main()

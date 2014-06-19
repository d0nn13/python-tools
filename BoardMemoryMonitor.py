#!/usr/bin/env python
from naoqi import ALBroker, ALProxy
from sys import stdout, exit
from UnbufferedStreamWrapper import *
import argparse


class BoardMemoryMonitor:
    def __init__(self, args):
        try:
            self._mem = ALProxy('ALMemory', args.url, args.port)
        except Exception as e:
            print e
            exit(1)
        self._prefix = 'Device/DeviceList'
        self._board = args.board
        self._key = args.key
        self._out = UnbufferedStreamWrapper(stdout)


    def run(self):
        progVersion = self._mem.getData('/'.join([self._prefix, self._board, 'ProgVersion']))
        print '\nMonitoring key \'' + self._key + '\' on board \'' + self._board + '\' [ProgVersion: ' + str(progVersion) + ']'

        try:
            while True:
                data = self._mem.getData('/'.join([self._prefix, self._board, self._key]))
                self._out.write(str(data))
                self._out.write('   \r')
        except RuntimeError as e:
            print e
        except KeyboardInterrupt:
           print '\r\nExiting monitor'
           exit(0)


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

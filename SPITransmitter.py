#!/usr/bin/env python
from mpsse import *
from sys import stdout, exit
from time import sleep
import argparse

class SPITransmitter(object):
    def __init__(self, mode, freq, pause):
        self._mode = mode
        self._freq = freq
        self._pause = pause
        try:
            self._m = MPSSE(self._mode + 1, self._freq)
        except Exception as e:
            print '\rCould not start FTDI Device : ' + e.args[0]
            exit(0)

    def run(self):
        stdout.write('Transmitter started : Mode = SPI' + str(self._mode))
        stdout.write('  |  Frequency = ' + str(self._m.GetClock()) + ' Hz')
        stdout.write('  |  Pause = ' + str(self._pause) + ' s\n')
        a = ord('A')
        s = 1
        while (1):
            try:

                if (((chr(a) >= 'z') and (s == 1)) or ((chr(a) <= 'A') and (s == -1))):
                    a -= s
                    s = -s
                    sleep(self._pause)
                w = str(chr(a) + chr(a + s))
                self._m.Start()
                self._m.Write(w)
                self._m.Stop()
                a += s * 2

            except KeyboardInterrupt:
               print '\r\nExiting transmitter'
               self._m.Close()
               exit(0)
            except Exception as e:
                if (e.args[0] == 'all fine'):
                    print "Exception caught : Couldn't read from device"
                    print "Exiting transmitter"
                else:
                    raise e
                self._m.Close()
                exit(1)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description='Transmit characters on FTDI SPI.')
    p.add_argument('-m', '--mode',
                    type=int,
                    choices=[0, 1, 2, 3],
                    default=0,
                    help='SPI Mode (see pylibmpsse doc for further info)')
    p.add_argument('-f', '--frequency',
                    type=int,
                    default='460000',
                    help='Clock frequency in Hz')
    p.add_argument('-p', '--pause',
                    type=int,
                    default='1',
                    help='Pause time between two frames in seconds')
    args = p.parse_args()
    t = SPITransmitter(args.mode, args.frequency, args.pause)
    t.run()

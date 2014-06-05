#!/usr/bin/env python
from mpsse import *
from sys import stdin, exit
from time import sleep
import argparse

class SPITransmitter:
    def __init__(self, mode, freq):
        self._usermode = mode
        self._userfreq = freq
        try:
            self._m = MPSSE(mode, freq)
        except Exception as e:
            print '\rCould not start FTDI Device : ' + e.args[0]
            exit(0)

    def run(self):
        print "Transmitter started : Mode=" + str(self._usermode) + " | Frequency=" + str(self._m.GetClock())
        a = ord('A')
        s = 1
        while (1):
            try:
                self._m.Start()
                self._m.Write(chr(a))
                self._m.Write(chr(a + s))
                self._m.Stop()
                a += s * 2
                if (((chr(a) >= 'y') and (s == 1)) or ((chr(a) <= 'b') and (s == -1))):
                    s = -s
                    sleep(1)
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
                    choices=[SPI0, SPI1, SPI2, SPI3],
                    default=SPI0,
                    help='SPI Mode (see pylibmpsse doc for further info)')
    p.add_argument('-f', '--frequency',
                    type=int,
                    default='460000')
    args = p.parse_args()
    t = SPITransmitter(args.mode, args.frequency)
    t.run()

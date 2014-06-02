#!/usr/bin/env python
from mpsse import *
from sys import stdin, exit

class SPITransmitter:
    def __init__(self, mode = SPI0, frequency = 460000):
        try:
            self._m = MPSSE(mode, frequency)
        except Exception as e:
            print '\rCould not start FTDI Device : ' + e.args[0]
            exit(0)

    def run(self):
        print "Transmitter started : Frequency=" + str(self._m.GetClock())
        a = ord('A') 
        while (1):
            try:
                self._m.Start()
                self._m.Write(chr(a))
                self._m.Write(chr(a + 1))
                self._m.Stop()
                a = a + 1 if (a < ord('z')) else ord('A')
            except KeyboardInterrupt:
               print '\r\nExiting transmitter'
               self._m.Close()
               exit(0)
            except Exception as e:
                self._m.Close()
                raise e
                exit(1)

if __name__ == "__main__":
    t = SPITransmitter()
    t.run()


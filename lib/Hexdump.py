from lib.UnbufferedStreamWrapper import *
from sys import stdout

class Hexdump:
	def __init__(self, length=16, sep='.'):
		self._length = length
		self._sep = sep
		self._out = UnbufferedStreamWrapper(stdout)
	def write(self, src):
		FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or self._sep for x in range(256)])
		for c in xrange(0, len(src), self._length):
			chars = src[c:c+self._length]
			h = ' '.join(["%02x" % ord(x) for x in chars])
			if len(h) > 24:
				h = "%s %s" % (h[:24], h[24:])
			printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or self._sep) for x in chars])
			self._out.write("%08x:  %-*s  |%s|\n" % (c, self._length*3, h, printable))


if __name__ == '__main__':
	h = Hexdump()
	h.write('test')

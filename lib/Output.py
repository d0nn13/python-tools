from sys import stdout

'''
Buffered stream to unbuffered
'''

class UnbufferedStreamWrapper(object):
    def __init__(self, stream):
        if not type(stream) is file:
            raise AttributeError('Cannot construct Wrapper with object ' +
                                 str(type(stream)))
        self._stream = stream

    def write(self, data):
        self._stream.write(data)
        self._stream.flush()

    def writeln(self, data):
        self._stream.write(data)
        self._stream.write('\n')
        self._stream.flush()

    def __getattr__(self, attr):
        return getattr(self._stream, attr)


'''
Hexdump formatted output
'''
    
class Hexdump:
    def __init__(self, stream=stdout, length=16, sep='.'):
        self._length = length
        self._sep = sep
        self._out = stream

    def write(self, src):
        FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or
                         self._sep for x in range(256)])
        for c in xrange(0, len(src), self._length):
            chars = src[c:c+self._length]
            h = ' '.join(["%02x" % ord(x) for x in chars])
            if len(h) > 24:
                h = "%s %s" % (h[:24], h[24:])
            printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or
                                self._sep) for x in chars])
            self._out.write("%08x:  %-*s  |%s|\n" %
                            (c, self._length*3, h, printable))

if __name__ == '__main__':
    h = Hexdump()
    h.write('test')

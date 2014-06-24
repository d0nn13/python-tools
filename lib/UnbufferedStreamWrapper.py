'''
Wraps a stream object into an auto-flushing one
'''
class UnbufferedStreamWrapper(object):
    def __init__(self, stream):
        if not type(stream) is file:
            raise AttributeError('Cannot construct Wrapper with object ' + str(type(stream)))
        self._stream = stream
    def write(self, data):
        self._stream.write(data)
        self._stream.flush()
    def __getattr__(self, attr):
        return getattr(self._stream, attr)

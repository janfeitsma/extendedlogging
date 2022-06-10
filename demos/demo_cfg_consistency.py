import extendedlogging

class ExpectedException(Exception):
    pass
@extendedlogging.traced
class myclass():
    def recurse(self, n):
        if n > 1:
            self.recurse(n-1)
        if n == 3:
            raise ExpectedException('something went terribly wrong at n=' + str(n))



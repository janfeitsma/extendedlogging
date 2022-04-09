import extendedlogging

# define a little example class and instrument all its functions with autologging
@extendedlogging.traced
class myclass():
    def __init__(self, *args, **kwargs):
        self.f()
        extendedlogging.debug('__init__ done')
    def f(self):
        extendedlogging.info('hi!')
        pass
    def g(self):
        return 3

# configure tracing
extendedlogging.configure(tracing=True)

# run some code to produce logging events
c = myclass('some_argument')
c.g()
extendedlogging.warning('done')


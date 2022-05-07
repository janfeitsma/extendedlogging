import extendedlogging

# visualizing the fibonacci sequence
@extendedlogging.traced
def fib(n):
    if n < 2:
        return n
    return fib(n-1) + fib(n-2)

# configure tracing
extendedlogging.configure(tracing=True)

# run some code to produce logging events
import sys
n = 7
if len(sys.argv) > 1:
    n = int(sys.argv[1])
print(fib(n))


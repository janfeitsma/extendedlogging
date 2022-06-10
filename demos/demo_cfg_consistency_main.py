# the configuration shall also apply to imported modules
# in particular, the error handler
# see testcase test_cfg_consistency

import extendedlogging
import demo_cfg_consistency

extendedlogging.configure(tracing=True, file_format='%(levelname)s:%(funcName)s: %(message)s')

c = demo_cfg_consistency.myclass()
c.recurse(4)

# expectation: an ERROR must be logged in trace file



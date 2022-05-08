# automatic import of all content in current folder
# merging https://github.com/samwyse/sspp and https://stackoverflow.com/a/43059528

from glob import glob
from keyword import iskeyword
from os.path import dirname, join, split, splitext
import logging
import traceback
import importlib
logging.basicConfig()

basedir = dirname(__file__)

for name in glob(join(basedir, '*.py')):
    module = splitext(split(name)[-1])[0]
    if not module.startswith('_') and not iskeyword(module):
        try:
            # get a handle on the module
            mdl = importlib.import_module(__name__+'.'+module)
            # is there an __all__?  if so respect it
            if "__all__" in mdl.__dict__:
                names = mdl.__dict__["__all__"]
            else:
                # otherwise we import all names that don't begin with _
                names = [x for x in mdl.__dict__ if not x.startswith("_")]
            # now drag them in
            globals().update({k: getattr(mdl, k) for k in names})
        except:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning('Ignoring exception while loading the %r plug-in:', module)
            print(traceback.format_exc())


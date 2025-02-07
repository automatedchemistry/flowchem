# Add all flowchem-device classes to the flowchem.device namespace
# This is needed by config parser and hides the complexity of the folder hierarchy to the library users.
# All * are defined as __all__ in the corresponding submodule to simplify name changes / refactoring.
from .bronkhorst import *
from .dataapex import *
from .hamilton import *
from .harvardapparatus import *
from .huber import *
from .knauer import *
from .magritek import *
from .manson import *
from .mettlertoledo import *
from .phidgets import *
from .vacuubrand import *
from .vapourtec import *
from .vicivalco import *
from .custom import *
from .waters import *
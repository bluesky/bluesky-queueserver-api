from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

from .api_base import WaitMonitor  # noqa: F401, E402
from .item import BFunc, BInst, BItem, BPlan  # noqa: F401, E402

# Device configuration - optional import
try:
    from .device_config import DeviceConfigurationManager, DeviceDefinition, create_shared_device_config  # noqa: F401, E402
except ImportError:
    # Dependencies not available
    pass

# Device coordination - optional import
try:
    from . import coordination  # noqa: F401, E402
except ImportError:
    # Dependencies not available
    pass

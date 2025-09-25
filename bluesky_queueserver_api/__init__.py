from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

from .api_base import WaitMonitor  # noqa: F401, E402
from .item import BFunc, BInst, BItem, BPlan  # noqa: F401, E402

# Device configuration moved to bluesky-queueserver repository
# (was tightly coupled with server-side device discovery logic)

# Note: Device coordination client was extracted from this package.
# Import paths under `bluesky_queueserver_api.coordination` are no longer provided here.

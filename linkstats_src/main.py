from typing import Optional

from chacc_api import BackboneContext

from . import models  # noqa: F401  (registers the linkstats_clicks table)
from .context_factory import get_context, set_module_context
from .routes import router as linkstats_router
from .service import DEFAULT_IP_SALT, LISTENER_NAME, make_recorder


# --- Module Setup ---
def setup_plugin(context: Optional[BackboneContext] = None):
    """
    Called by the ChaCC backbone. shortlinks is a required dependency, so it has
    already been set up and its services are registered.
    """
    _module_context = get_context(context)
    set_module_context(_module_context)

    _module_context.logger.info("linkstats: Setup initiated!")

    add_listener = _module_context.get_service("shortlinks.add_visit_listener")
    if add_listener is None:
        _module_context.logger.error(
            "linkstats: shortlinks service not found; clicks will not be recorded."
        )
    else:
        # Optional LINKSTATS_IP_SALT in .env keeps visitor IP hashes unguessable.
        salt = _module_context.get_module_config("IP_SALT", "linkstats", DEFAULT_IP_SALT)
        add_listener(LISTENER_NAME, make_recorder(salt))

    return linkstats_router


def get_plugin_info():
    """Provides essential information about this module to the ChaCC API backbone."""
    return {
        "name": "linkstats",
        "display_name": "Link Stats",
        "version": "0.1.0",
        "author": "Jonas",
        "description": "Click analytics for shortlinks: totals, per day, referers and browsers.",
        "status": "enabled",
    }

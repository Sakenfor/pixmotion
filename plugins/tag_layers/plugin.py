from interfaces import IPlugin
from .services import register_services
from .layers import register_layers
from .ui import register_ui

class Plugin(IPlugin):
    def register(self, framework):
        for service in register_services(framework):
            framework.register_contribution("services", service)
        register_layers(framework)
        register_ui(framework)

def register_plugin(service_registry):
    framework = service_registry.get("framework")
    if framework is None:
        raise RuntimeError("Framework service not registered.")
    Plugin().register(framework)

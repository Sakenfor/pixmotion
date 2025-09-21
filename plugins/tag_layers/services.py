from framework.tag_layer_registry import TagLayerRegistry
from services.tag_layers.tag_index_service import TagIndexService
from services.tag_layers.scan_profile_service import ScanProfileService

def register_services(framework):
    log = framework.get_service("log_manager")
    return [
        {"id": "tag_layer_registry", "instance": TagLayerRegistry(log)},
        {"id": "tag_index_service", "instance": TagIndexService(framework)},
        {"id": "scan_profile_service", "instance": ScanProfileService(framework)},
    ]

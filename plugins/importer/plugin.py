# D:/My Drive/code/pixmotion/plugins/importer/plugin.py
from interfaces import IPlugin
from .services import WebImporterService

class Plugin(IPlugin):
    def register(self, framework):
        importer_service = WebImporterService(framework)
        framework.register_contribution("services", {"id": "web_importer_service", "instance": importer_service})
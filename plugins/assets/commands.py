# story_studio_project/plugins/assets/commands.py
from interfaces import ICommand

class ScanFolderCommand(ICommand):
    """Command to trigger a folder scan via the AssetService."""
    def __init__(self, framework):
        self.asset_service = framework.get_service("asset_service")

    def execute(self, folder_path):
        if self.asset_service:
            self.asset_service.scan_folder(folder_path)

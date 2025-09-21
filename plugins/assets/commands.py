# story_studio_project/plugins/assets/commands.py
from interfaces import ICommand


class ScanFolderCommand(ICommand):
    """Command to trigger a folder scan via the AssetService."""

    def __init__(self, framework):
        self.asset_service = framework.get_service("asset_service")

    def execute(self, folder_path):
        if self.asset_service:
            self.asset_service.scan_folder(folder_path)


class RescanEmotionPackagesCommand(ICommand):
    """Command to force a re-sync of emotion package manifests."""

    def __init__(self, framework):
        self.emotion_service = framework.get_service("emotion_package_service")

    def execute(self, package_uuid: str | None = None):
        if not self.emotion_service:
            return
        if package_uuid:
            self.emotion_service.sync_package_by_uuid(package_uuid)
        else:
            self.emotion_service.sync_all_packages()

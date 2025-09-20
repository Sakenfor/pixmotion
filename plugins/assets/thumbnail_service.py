# D:/My Drive/code/pixmotion/plugins/assets/thumbnail_service.py
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QSize

class ThumbnailService:
    """
    A service for loading and caching thumbnails to avoid blocking the UI.
    It's designed to be used by a background worker.
    """
    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.cache = {}
        self.cache_size = 2000  # Max number of thumbnails to keep in memory

    def get_thumbnail(self, path, size=QSize(128, 128)):
        """
        Gets a QPixmap for a given path. Checks cache first.
        This method is intended to be called from a background thread.
        """
        if not path:
            return None

        if path in self.cache:
            return self.cache[path]

        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                return None
            
            # Add to cache
            if len(self.cache) > self.cache_size:
                # Simple cache eviction: remove the oldest item
                self.cache.pop(next(iter(self.cache)))
            
            self.cache[path] = pixmap
            return pixmap
        except Exception as e:
            self.log.error(f"Failed to load thumbnail for {path}: {e}")
            return None
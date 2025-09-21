# D:/My Drive/code/pixmotion/plugins/importer/services.py
import os
import requests
from bs4 import BeautifulSoup
import uuid


class WebImporterService:
    """A service to handle importing assets from web URLs."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.project_root = framework.get_project_root()

    def import_from_url(self, url: str) -> str | None:
        """
        Detects the source from a URL, downloads the media, saves it to a
        managed folder, and returns the new local path.
        """
        if "pinterest.com" not in url:
            self.log.info(f"URL is not a Pinterest link. Skipping web import.")
            return None

        self.log.info(f"Importing image from Pinterest URL: {url}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            page_response = requests.get(url, headers=headers, timeout=15)
            page_response.raise_for_status()

            soup = BeautifulSoup(page_response.text, "html.parser")
            img_tag = soup.find("meta", property="og:image")

            if not img_tag or not img_tag.get("content"):
                self.log.error(
                    "Could not find high-resolution image meta tag on Pinterest page."
                )
                return None

            image_url = img_tag["content"]
            image_response = requests.get(image_url, timeout=30, stream=True)
            image_response.raise_for_status()

            pinterest_dir = os.path.join(self.project_root, "assets", "pinterest")
            os.makedirs(pinterest_dir, exist_ok=True)
            filename = f"pinterest_{uuid.uuid4().hex[:12]}.jpg"
            filepath = os.path.join(pinterest_dir, filename)

            with open(filepath, "wb") as f:
                for chunk in image_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.log.info(
                f"Successfully downloaded and saved Pinterest image to: {filepath}"
            )
            return filepath

        except requests.exceptions.RequestException as e:
            self.log.error(f"Network error while importing from Pinterest: {e}")
            return None
        except Exception as e:
            self.log.error(
                f"An unexpected error occurred during Pinterest import: {e}",
                exc_info=True,
            )
            return None

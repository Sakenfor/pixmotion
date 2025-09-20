# D:/My Drive/code/pixmotion/plugins/generation/services.py
import os
import uuid
import time
import requests
from sqlalchemy.orm import Session
from plugins.core.models import Asset, Generation, AssetType
from plugins.core.services import DatabaseService
import io
from PIL import Image


class PixverseService:
    """Service to interact with the Pixverse API and log generations to the database."""
    BASE_URL = "https://app-api.pixverse.ai/openapi/v2"

    MAX_DIMENSION = 4000
    MAX_FILE_SIZE_MB = 20
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.events = framework.get_service("event_manager")

    def _get_required_service(self, service_name: str):
        """Helper to get a service from the framework and raise an error if it's not found."""
        service = self.framework.get_service(service_name)
        if service is None:
            raise RuntimeError(
                f"The required service '{service_name}' could not be found. Check application startup order.")
        return service

    def generate_video(self, **kwargs):
        worker = self._get_required_service("worker_manager")
        worker.submit(self._generation_task, **kwargs)

    def _generation_task(self, **kwargs):
        try:
            asset_service = self._get_required_service("asset_service")
            headers = self._get_headers()
            if not headers.get("API-KEY"): raise ValueError("API Key is missing.")

            prompt = kwargs.get("prompt", "a beautiful landscape")

            path1, path2 = None, None
            asset_id1 = kwargs.get("input_asset1_id")
            asset_id2 = kwargs.get("input_asset2_id")

            if asset_id1:
                path1 = asset_service.get_asset_path(asset_id1)
                if not path1:
                    raise FileNotFoundError(
                        f"Asset ID '{asset_id1}' was provided, but no corresponding path was found.")

            if asset_id2:
                path2 = asset_service.get_asset_path(asset_id2)
                if not path2:
                    self.log.warning(f"Asset ID '{asset_id2}' was provided, but no corresponding path was found.")

            if path1 and not os.path.exists(path1):
                raise FileNotFoundError(f"Input image path does not exist: {path1}")

            payload = {
                "prompt": prompt, "model": kwargs.get("model", "v5"),
                "quality": kwargs.get("quality", "360p"), "duration": 5
            }
            if kwargs.get("camera_movement") != "None": payload["camera_movement"] = kwargs.get("camera_movement")

            if path1 and path2:
                payload["first_frame_img"] = self._upload_image(path1, headers)
                payload["last_frame_img"] = self._upload_image(path2, headers)
                endpoint = "/video/transition/generate"
            elif path1:
                payload["img_id"] = self._upload_image(path1, headers)
                endpoint = "/video/img/generate"
            else:
                raise ValueError("No input images provided.")

            resp = requests.post(self.BASE_URL + endpoint, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()

            json_data = resp.json()
            self.log.debug(f"Generation start response: {json_data}")

            if json_data.get("ErrCode", 0) != 0:
                error_message = json_data.get("ErrMsg", "Unknown API error when starting generation.")
                raise Exception(f"API Error: {error_message} (ErrCode: {json_data.get('ErrCode')})")

            if 'Resp' not in json_data or 'video_id' not in json_data.get('Resp', {}):
                raise KeyError("The key 'Resp' or 'video_id' was not found in the successful API response.")

            video_id = json_data['Resp']['video_id']
            start_time = time.time()
            timeout_seconds = 300

            while time.time() - start_time < timeout_seconds:
                time.sleep(5)
                resp = requests.get(f"{self.BASE_URL}/video/result/{video_id}", headers=headers, timeout=15)
                resp.raise_for_status()

                data = resp.json()
                self.log.debug(f"Polling response: {data}")

                if data.get("ErrCode", 0) != 0:
                    error_message = data.get("ErrMsg", "Unknown API error during polling.")
                    raise Exception(f"API Error: {error_message} (ErrCode: {data.get('ErrCode')})")

                if 'Resp' not in data:
                    raise KeyError("The key 'Resp' was not found in the successful polling response.")

                resp_data = data['Resp']
                status = resp_data.get('status')
                self.log.info(f"Polling video '{video_id}', current status: {status}")

                if status == 1:
                    video_url = resp_data['url'];
                    break
                elif status in [7, 8] or (status is not None and status < 0):
                    raise Exception(
                        f"API generation failed. Status: {status}, Message: {resp_data.get('msg', 'No message')}")
            else:
                raise TimeoutError(f"Video generation timed out after {timeout_seconds} seconds.")

            # --- Download and Database Logging ---
            title = kwargs.get("title")
            final_path = self._get_output_path(video_id, title)
            video_data = requests.get(video_url, timeout=60)
            video_data.raise_for_status()
            with open(final_path, 'wb') as f:
                f.write(video_data.content)
            self.log.info(f"Video downloaded to {final_path}")

            # --- Add to database using the public AssetService method ---
            output_asset = asset_service.add_asset(final_path)

            if output_asset:
                # Now, in a separate unit of work, log the generation event
                db_service = self._get_required_service("database_service")
                with db_service.get_session() as session:
                    gen_record = Generation(
                        prompt=prompt,
                        model=kwargs.get("model"),
                        quality=kwargs.get("quality"),
                        duration=kwargs.get("duration"),
                        output_asset_id=output_asset.id,
                        input_asset1_id=kwargs.get("input_asset1_id"),
                        input_asset2_id=kwargs.get("input_asset2_id")
                    )
                    session.add(gen_record)
                    session.commit()
                    self.log.info(f"Generation record created for {final_path}")

            self.events.publish("pixverse:generation_finished", success=True, output_path=final_path)
            self.log.notification(f"Video saved: {os.path.basename(final_path)}")

        except Exception as e:
            self.log.error(f"Pixverse generation failed: {e}", exc_info=True)
            self.events.publish("pixverse:generation_failed", error_message=str(e))

    def _get_headers(self):
        settings = self._get_required_service("settings_service")
        api_key = settings.get("pixverse_api_key", "")
        return {"API-KEY": api_key, "Ai-trace-id": str(uuid.uuid4())}

    def _get_output_path(self, video_id, title=None):
        settings = self._get_required_service("settings_service")
        output_dir = settings.get("output_directory", "generated_media")
        os.makedirs(output_dir, exist_ok=True)

        if title and title.strip():
            base_name = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
            filename = f"{base_name}_{video_id}.mp4"
        else:
            filename = f"{video_id}.mp4"

        return os.path.join(output_dir, filename)

    def _upload_image(self, image_path, headers):
        """Pre-processes an image to meet API constraints and then uploads it."""
        try:
            with Image.open(image_path) as img:
                if max(img.size) > self.MAX_DIMENSION:
                    self.log.info(f"Image dimensions ({img.width}x{img.height}) exceed max. Resizing.")
                    img.thumbnail((self.MAX_DIMENSION, self.MAX_DIMENSION), Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                quality = 95
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(buffer, format='JPEG', quality=quality)

                while buffer.getbuffer().nbytes > self.MAX_FILE_SIZE_BYTES and quality > 50:
                    self.log.info(
                        f"Image file size ({buffer.getbuffer().nbytes / 1024 / 1024:.2f}MB) exceeds limit. Reducing quality to {quality - 5}.")
                    buffer.seek(0)
                    buffer.truncate(0)
                    quality -= 5
                    img.save(buffer, format='JPEG', quality=quality)

                if buffer.getbuffer().nbytes > self.MAX_FILE_SIZE_BYTES:
                    raise ValueError(f"Could not reduce image size below {self.MAX_FILE_SIZE_MB}MB.")

                buffer.seek(0)
                file_name = os.path.basename(image_path)

                resp = requests.post(f"{self.BASE_URL}/image/upload", headers=headers,
                                     files={'image': (file_name, buffer, 'image/jpeg')}, timeout=60)

        except Exception as e:
            self.log.error(f"Failed during image preprocessing or upload for {image_path}: {e}", exc_info=True)
            raise

        resp.raise_for_status()

        json_data = resp.json()
        self.log.debug(f"Image upload response: {json_data}")

        if json_data.get("ErrCode", 0) != 0:
            error_message = json_data.get("ErrMsg", "Unknown API error during image upload.")
            raise Exception(f"API Error: {error_message} (ErrCode: {json_data.get('ErrCode')})")

        if 'Resp' not in json_data or 'img_id' not in json_data.get('Resp', {}):
            raise KeyError("The key 'Resp' or 'img_id' was not found in the successful API response.")

        return json_data['Resp']['img_id']
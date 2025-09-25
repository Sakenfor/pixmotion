"""
Commands for the Visual Prompt Composer plugin.
"""
from interfaces import ICommand


class NewSceneCommand(ICommand):
    def execute(self, **kwargs):
        composer_service = self.framework.get_service("visual_composer_service")
        if composer_service:
            name = kwargs.get("name", "New Scene")
            scene = composer_service.new_scene(name)
            return {"status": "success", "scene_id": scene.id if scene else None}
        return {"status": "error", "message": "Composer service not available"}


class SaveSceneCommand(ICommand):
    def execute(self, **kwargs):
        composer_service = self.framework.get_service("visual_composer_service")
        if composer_service:
            filepath = kwargs.get("filepath")
            success = composer_service.save_scene(filepath=filepath)
            return {"status": "success" if success else "error"}
        return {"status": "error", "message": "Composer service not available"}


class LoadSceneCommand(ICommand):
    def execute(self, **kwargs):
        composer_service = self.framework.get_service("visual_composer_service")
        if composer_service:
            filepath = kwargs.get("filepath")
            if not filepath:
                return {"status": "error", "message": "filepath is required"}

            scene = composer_service.load_scene(filepath)
            return {
                "status": "success" if scene else "error",
                "scene_id": scene.id if scene else None
            }
        return {"status": "error", "message": "Composer service not available"}


class GeneratePromptCommand(ICommand):
    def execute(self, **kwargs):
        composer_service = self.framework.get_service("visual_composer_service")
        if composer_service:
            time_segment = kwargs.get("time_segment")
            prompt = composer_service.generate_prompt(time_segment)
            return {"status": "success", "prompt": prompt}
        return {"status": "error", "message": "Composer service not available"}


class ExportToGeneratorCommand(ICommand):
    def execute(self, **kwargs):
        composer_service = self.framework.get_service("visual_composer_service")
        if composer_service:
            prompt = kwargs.get("prompt")
            success = composer_service.export_to_generator(prompt)
            return {"status": "success" if success else "error"}
        return {"status": "error", "message": "Composer service not available"}
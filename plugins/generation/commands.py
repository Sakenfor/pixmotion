# story_studio_project/plugins/generation/commands.py
from interfaces import ICommand

class GenerateVideoCommand(ICommand):
    """Command to trigger the PixverseService to generate a video."""
    def __init__(self, framework):
        self.service = framework.get_service("pixverse_service")

    def execute(self, **kwargs):
        if self.service:
            self.service.generate_video(**kwargs)

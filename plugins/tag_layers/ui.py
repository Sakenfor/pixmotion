from .panel import TagLayersPanel

def register_ui(framework):
    framework.register_contribution(
        "ui_docks",
        {
            "id": "tag_layers",
            "class": TagLayersPanel,
            "title": "Tag Layers",
            "default_area": "right",
        },
    )

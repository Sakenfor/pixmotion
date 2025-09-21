def register_layers(framework):
    registry = framework.get_service("tag_layer_registry")
    if not registry:
        return
    registry.register_layer("basic", {"name": "Basic File Tags", "generator": "services.tag_layers.ai_quick_generator:AIQuickGenerator"})
    registry.register_layer("ai_quick", {"name": "AI Quick", "generator": "services.tag_layers.ai_quick_generator:AIQuickGenerator"})
    registry.register_layer("ai_deep", {"name": "AI Deep", "generator": "services.tag_layers.ai_deep_generator:AIDeepGenerator"})

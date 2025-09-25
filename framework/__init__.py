# story_studio_project/framework/__init__.py
import sys
import os
import importlib
import logging
import traceback
from graphlib import CycleError, TopologicalSorter
from typing import Any, Optional
from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from .asset_manager import AssetManager
from .template_registry import TemplateRegistry
from .graph_registry import GraphRegistry
from .graph_store import GraphStore
from .graph_service import GraphService
from .gameplay import GameplayRuntime
from interfaces import ICommand, IUndoableCommand


# --- Core Services ---

class LogManager:
    """Handles logging and user-facing notifications."""

    def __init__(self):
        self._setup_logging()
        self._notification_callbacks = []

    def _setup_logging(self):
        """Setup logging with proper configuration and file output."""
        import os
        from pathlib import Path

        # Get log level from environment or default to INFO
        log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()

        # Create logs directory in user data folder
        try:
            from framework.config_manager import ConfigManager
            config_manager = ConfigManager()
            log_dir = config_manager.cache_dir / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "pixmotion.log"
        except Exception:
            # Fallback to current directory if config manager fails
            log_file = Path("pixmotion.log")

        # Clear any existing handlers to avoid duplicates
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Setup logging configuration
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()  # Console output
            ]
        )

        # Create application logger
        self.logger = logging.getLogger('PixMotion')
        self.logger.info(f"Logging initialized. Level: {log_level}, File: {log_file}")

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def debug(self, message):
        """Logs a message with the DEBUG level."""
        self.logger.debug(message)

    def notification(self, message):
        self.info(f"NOTIFICATION: {message}")
        for callback in self._notification_callbacks: callback(message)

    def subscribe_to_notifications(self, callback):
        self._notification_callbacks.append(callback)

    def set_level(self, level_name):
        """Sets the logging level for the root logger and all known handlers."""
        level = logging.getLevelName(level_name.upper())
        if not isinstance(level, int):
            self.error(f"Invalid log level name: {level_name}")
            return

        logging.getLogger().setLevel(level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)
        self.info(f"Log level set to {level_name.upper()}")


class EventManager:
    """Manages the publish-subscribe system for decoupled communication."""

    def __init__(self, log_manager):
        self.log = log_manager
        self.subscribers = {}

    def subscribe(self, event_name, callback):
        if event_name not in self.subscribers: self.subscribers[event_name] = []
        self.subscribers[event_name].append(callback)

    def publish(self, event_name, **kwargs):
        self.log.info(f"Event published: '{event_name}' with data: {kwargs}")
        if event_name in self.subscribers:
            for callback in self.subscribers[event_name]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    self.log.error(f"Error in event callback for '{event_name}': {e}", exc_info=True)

    def publish_chain(self, event_name, data_object):
        """
        Publishes an event where each subscriber can modify the data object.
        Subscribers can cancel the chain by setting data_object['is_cancelled'] = True.
        Returns the final (potentially modified) data object.
        """
        self.log.info(f"Publishing cancellable event chain: '{event_name}'")
        if 'is_cancelled' not in data_object:
            data_object['is_cancelled'] = False

        if event_name in self.subscribers:
            for callback in self.subscribers[event_name]:
                if data_object['is_cancelled']:
                    self.log.info(f"Event chain '{event_name}' was cancelled. Halting execution.")
                    break
                try:
                    callback(data_object)
                except Exception as e:
                    self.log.error(f"Error in chain callback for '{event_name}': {e}", exc_info=True)

        return data_object


class ServiceManager:
    """A central registry for all services in the application."""

    def __init__(self, log_manager):
        self.log = log_manager
        self._services = {}

    def register(self, service_id, instance):
        self.log.info(f"Registering service: '{service_id}'")
        self._services[service_id] = instance

    def get(self, service_id):
        return self._services.get(service_id)

    def clear_all_except(self, persistent_services):
        """Removes all services except for a persistent few (like logging)."""
        self._services = {k: v for k, v in self._services.items() if k in persistent_services}


class CommandManager:
    """Discovers, stores, and executes all registered commands."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.history_manager = None
        self._commands = {}

    def register(self, command_id, command_class):
        self.log.info(f"Registering command: '{command_id}'")
        self._commands[command_id] = command_class

    def execute(self, command_id, **kwargs):
        self.log.info(f"Executing command: '{command_id}' with args: {kwargs}")
        command_class = self._commands.get(command_id)
        if command_class:
            command_instance = command_class(self.framework)
            result = command_instance.execute(**kwargs)
            if isinstance(command_instance, IUndoableCommand) and self.history_manager:
                self.history_manager.add_command(command_instance)
            return result
        else:
            self.log.error(f"Command not found: {command_id}")

    def clear(self):
        """Unregisters all commands."""
        self._commands.clear()


class WorkerManager:
    """Manages a Qt thread pool for running background tasks."""

    def __init__(self, log_manager):
        self.log = log_manager
        self.threadpool = QThreadPool()
        self.running_workers = set()
        self.log.info(f"WorkerManager started with {self.threadpool.maxThreadCount()} threads.")

    def submit(self, fn, on_result=None, on_error=None, *args, **kwargs):
        """
        Submits a function to run on a background thread.
        Connects to on_result and on_error callbacks if provided.
        """
        signals = WorkerSignals()
        if on_result:
            signals.result.connect(on_result)

        if on_error:
            signals.error.connect(on_error)
        else:
            signals.error.connect(lambda err: self.log.error(f"Error in background task: {err[1]}", exc_info=err))

        def on_finished():
            if worker in self.running_workers:
                self.running_workers.remove(worker)

        signals.finished.connect(on_finished)
        worker = Worker(fn, signals, *args, **kwargs)
        self.running_workers.add(worker)
        self.threadpool.start(worker)
        self.log.info(f"Submitted task '{fn.__name__}' to background worker.")


class HistoryManager:
    """Manages the undo and redo stacks for IUndoableCommand objects."""

    def __init__(self, log_manager, event_manager):
        self.log = log_manager
        self.events = event_manager
        self.undo_stack, self.redo_stack = [], []

    def add_command(self, command):
        self.undo_stack.append(command)
        self.redo_stack.clear()
        self.log.info(f"Added command to undo stack. Size: {len(self.undo_stack)}")
        self.events.publish("history:changed")

    def undo(self):
        if self.undo_stack:
            command = self.undo_stack.pop()
            command.undo()
            self.redo_stack.append(command)
            self.log.info("Undo successful.")
            self.events.publish("history:changed")

    def redo(self):
        if self.redo_stack:
            command = self.redo_stack.pop()
            command.redo()
            self.undo_stack.append(command)
            self.log.info("Redo successful.")
            self.events.publish("history:changed")


class PluginManager:
    """Discovers plugins from manifests and loads them in dependency order."""

    def __init__(self, framework, asset_manager):
        self.framework = framework
        self.asset_manager = asset_manager
        self.log = framework.get_service("log_manager")
        self.loaded_modules: set[str] = set()
        self.loaded_plugins: list[str] = []

    def load_plugins(self) -> None:
        manifests = self.asset_manager.plugin_manifests
        if not manifests:
            self.log.warning("No plugin manifests discovered; skipping plugin load.")
            return

        load_order = self._resolve_load_order(manifests)
        if not load_order:
            self.log.warning("No plugins passed validation; nothing to load.")
            return

        resolved_order = []
        for plugin_uuid in load_order:
            manifest = manifests.get(plugin_uuid)
            label = manifest.name or manifest.uuid if manifest else plugin_uuid
            resolved_order.append(label)
        self.log.info(f"Loading plugins in order: {resolved_order}")
        for plugin_uuid in load_order:
            manifest = manifests.get(plugin_uuid)
            if manifest:
                self._load_plugin(manifest)

    def _resolve_load_order(self, manifests) -> list[str]:
        name_index: dict[str, set[str]] = {}
        for uuid, manifest in manifests.items():
            key = (manifest.name or "").strip().lower()
            if not key:
                continue
            name_index.setdefault(key, set()).add(uuid)

        valid_manifests: dict[str, Any] = {}
        resolved_dependencies: dict[str, set[str]] = {}

        for uuid, manifest in sorted(
            manifests.items(), key=lambda item: (item[1].name or "", item[0])
        ):
            label = manifest.name or uuid
            required = []
            missing_required = []
            ambiguous_required = {}
            optional_resolved = []
            optional_ambiguous = {}

            def resolve_reference(raw_dep: str):
                dep = raw_dep.strip()
                if not dep:
                    return "skip", None
                if dep in manifests:
                    return "ok", dep
                candidates = list(name_index.get(dep.lower(), []))
                if len(candidates) == 1:
                    return "ok", candidates[0]
                if len(candidates) > 1:
                    options = [
                        manifests[c].name or manifests[c].uuid for c in candidates
                    ]
                    return "ambiguous", options
                return "missing", dep

            for raw_dep in manifest.dependencies:
                status, value = resolve_reference(raw_dep)
                if status == "ok":
                    required.append(value)
                elif status == "ambiguous":
                    ambiguous_required[raw_dep] = value
                elif status == "missing":
                    missing_required.append(value)

            for raw_dep in getattr(manifest, "optional_dependencies", []):
                status, value = resolve_reference(raw_dep)
                if status == "ok":
                    optional_resolved.append(value)
                elif status == "ambiguous":
                    optional_ambiguous[raw_dep] = value

            if ambiguous_required:
                for dep, options in ambiguous_required.items():
                    self.log.error(
                        f"Plugin '{label}' has ambiguous dependency '{dep}': {options}. Skipping."
                    )
                continue

            if missing_required:
                self.log.error(
                    f"Plugin '{label}' is missing dependencies: {missing_required}. Skipping."
                )
                continue

            if optional_ambiguous:
                for dep, options in optional_ambiguous.items():
                    self.log.warning(
                        f"Plugin '{label}' has ambiguous optional dependency '{dep}': {options}. Ignoring."
                    )

            valid_manifests[uuid] = manifest
            all_dependencies = set(required)
            all_dependencies.update(optional_resolved)
            resolved_dependencies[uuid] = all_dependencies

        if not valid_manifests:
            return []

        graph = {
            uuid: {dep for dep in resolved_dependencies.get(uuid, set()) if dep in valid_manifests}
            for uuid in valid_manifests.keys()
        }
        try:
            order = list(TopologicalSorter(graph).static_order())
        except CycleError as err:
            cycle_nodes = list(err.args[1]) if len(err.args) > 1 else []
            self.log.error(
                f"Detected circular plugin dependencies: {cycle_nodes}. Skipping the cycle."
            )
            for node in cycle_nodes:
                valid_manifests.pop(node, None)
                graph.pop(node, None)
            for deps in graph.values():
                deps.difference_update(cycle_nodes)
            order = list(TopologicalSorter(graph).static_order()) if graph else []

        return [uuid for uuid in order if uuid in valid_manifests]

    def _load_plugin(self, manifest) -> None:
        module_name, sep, attribute = manifest.entry_point.partition(":")
        if not sep:
            label = manifest.name or manifest.uuid
            self.log.error(
                f"Invalid entry point '{manifest.entry_point}' for plugin {label}."
            )
            return

        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001
            label = manifest.name or manifest.uuid
            self.log.error(
                f"Failed to import module '{module_name}' for plugin {label}: {exc}",
                exc_info=True,
            )
            return

        try:
            entry_callable = getattr(module, attribute)
        except AttributeError:
            label = manifest.name or manifest.uuid
            self.log.error(
                f"Entry point '{attribute}' not found in module '{module_name}' for plugin {label}."
            )
            return

        service_registry = self.framework.service_manager
        self.framework._push_plugin_context(manifest.uuid)
        try:
            entry_callable(service_registry)
        except Exception as exc:  # noqa: BLE001
            label = manifest.name or manifest.uuid
            self.log.error(
                f"Error while executing entry point for plugin {label}: {exc}",
                exc_info=True,
            )
            return
        finally:
            self.framework._pop_plugin_context()

        self._track_loaded_modules(module_name)
        self.loaded_plugins.append(manifest.uuid)
        label = manifest.name or manifest.uuid
        self.log.info(f"Successfully loaded plugin '{label}' ({manifest.uuid}).")

    def _track_loaded_modules(self, module_name: str) -> None:
        package_prefixes = {module_name}
        if "." in module_name:
            package_prefixes.add(module_name.rsplit(".", 1)[0])

        for name in list(sys.modules.keys()):
            if any(
                name == prefix or name.startswith(f"{prefix}.")
                for prefix in package_prefixes
            ):
                self.loaded_modules.add(name)

    def unload_all_plugins(self) -> None:
        self.log.info(f"Unloading {len(self.loaded_modules)} plugin modules...")
        for module_name in sorted(self.loaded_modules, reverse=True):
            if module_name in sys.modules:
                del sys.modules[module_name]
        self.loaded_modules.clear()
        self.loaded_plugins.clear()


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    """A generic QRunnable worker that can emit signals."""

    def __init__(self, fn, signals, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = signals

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class Framework:
    """The central class that initializes and holds all core services."""

    def __init__(self):
        self.log_manager = LogManager()
        self.event_manager = EventManager(self.log_manager)
        self.service_manager = ServiceManager(self.log_manager)
        self.worker_manager = WorkerManager(self.log_manager)
        self.history_manager = HistoryManager(self.log_manager, self.event_manager)

        self.service_manager.register("log_manager", self.log_manager)
        self.service_manager.register("event_manager", self.event_manager)
        self.service_manager.register("service_manager", self.service_manager)
        self.service_manager.register("worker_manager", self.worker_manager)
        self.service_manager.register("history_manager", self.history_manager)
        self.service_manager.register("framework", self)

        self.asset_manager = AssetManager(self.log_manager)
        self.template_registry = TemplateRegistry(self.log_manager)
        self.graph_registry = GraphRegistry(self.log_manager)
        self.graph_store = GraphStore(self.log_manager)
        self.graph_service = GraphService(self)
        self.gameplay_runtime = GameplayRuntime(self)
        self.command_manager = CommandManager(self)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.plugin_manager = PluginManager(self, self.asset_manager)

        self.service_manager.register("asset_manager", self.asset_manager)
        self.service_manager.register("template_registry", self.template_registry)
        self.service_manager.register("graph_registry", self.graph_registry)
        self.service_manager.register("graph_store", self.graph_store)
        self.service_manager.register("graph_service", self.graph_service)
        self.service_manager.register("gameplay_runtime", self.gameplay_runtime)
        self.service_manager.register("command_manager", self.command_manager)
        self.command_manager.history_manager = self.history_manager

        self.contributions = {}
        self.shell = None
        self._plugin_context: list[str] = []

    def get_service(self, service_id):
        return self.service_manager.get(service_id)

    def get_active_plugin_uuid(self) -> Optional[str]:
        return self._plugin_context[-1] if self._plugin_context else None

    def _push_plugin_context(self, plugin_uuid: str) -> None:
        if plugin_uuid:
            self._plugin_context.append(plugin_uuid)

    def _pop_plugin_context(self) -> None:
        if self._plugin_context:
            self._plugin_context.pop()

    def get_project_root(self):
        return self.project_root

    def register_contribution(self, point, data):
        """Registers a contribution from a plugin."""
        if point not in self.contributions:
            self.contributions[point] = []

        if isinstance(data, dict):
            payload = dict(data)
        else:
            payload = {"value": data}

        if "plugin_uuid" not in payload or not payload.get("plugin_uuid"):
            active_uuid = self.get_active_plugin_uuid()
            if active_uuid:
                payload.setdefault("plugin_uuid", active_uuid)

        self.contributions[point].append(payload)
        self.log_manager.info(
            f"Contribution registered to '{point}': {payload.get('id', 'N/A')}"
        )

        if point == "services":
            self.service_manager.register(payload["id"], payload["instance"])
        elif point == "template_bundles":
            template_type = payload.get("template_type") or payload.get("type")
            entries = payload.get("entries", [])
            plugin_uuid = payload.get("plugin_uuid") or ""
            if template_type and entries:
                self.template_registry.register_bundle(
                    template_type,
                    entries,
                    plugin_uuid=plugin_uuid,
                )
        elif point == "gameplay_orchestrators":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.gameplay_runtime.register_orchestrator(
                payload.get("id", ""),
                payload.get("class"),
                plugin_uuid=plugin_uuid,
                metadata=payload.get("metadata"),
            )
        elif point == "prompt_handlers":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.gameplay_runtime.register_prompt_handler(
                payload.get("id", ""),
                payload.get("class"),
                plugin_uuid=plugin_uuid,
                priority=int(payload.get("priority", 100)),
                metadata=payload.get("metadata"),
            )
        elif point == "prompt_suggesters":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.gameplay_runtime.register_prompt_suggester(
                payload.get("id", ""),
                payload.get("class"),
                plugin_uuid=plugin_uuid,
                metadata=payload.get("metadata"),
            )
        elif point == "minigames":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.gameplay_runtime.register_minigame(
                payload.get("id", ""),
                payload,
                plugin_uuid=plugin_uuid,
            )
        elif point == "graph_node_types":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.graph_registry.register_node_type(payload, plugin_uuid=plugin_uuid)
        elif point == "graph_relation_types":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.graph_registry.register_relation_type(payload, plugin_uuid=plugin_uuid)
        elif point == "graph_templates":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.graph_registry.register_template(payload, plugin_uuid=plugin_uuid)
        elif point == "graph_validators":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.graph_registry.register_validator(payload, plugin_uuid=plugin_uuid)
        elif point == "graph_runtime_handlers":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.graph_registry.register_runtime_handler(payload, plugin_uuid=plugin_uuid)
            self.gameplay_runtime.invalidate_runtime_handlers()
        elif point == "graph_personas":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.graph_registry.register_persona(payload, plugin_uuid=plugin_uuid)
        elif point == "graph_action_bundles":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.graph_registry.register_action_bundle(payload, plugin_uuid=plugin_uuid)
        elif point == "graph_qualitative_scales":
            plugin_uuid = payload.get("plugin_uuid") or ""
            self.graph_registry.register_qualitative_scale(payload, plugin_uuid=plugin_uuid)

    def get_contributions(self, point):
        return self.contributions.get(point, [])

    def initialize(self, app):
        """Loads plugins and starts the application shell."""
        framework_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(framework_dir)
        plugins_path = os.path.join(project_root, "plugins")

        if plugins_path not in sys.path:
            sys.path.insert(0, plugins_path)
        if self.project_root not in sys.path:
            sys.path.insert(0, self.project_root)

        self.graph_service.load_all()
        self._discover_assets_and_plugins(plugins_path)
        self.plugin_manager.load_plugins()

        db_service = self.get_service("database_service")
        if db_service:
            db_service.create_all_tables()

            # Ensure tag layer defaults are created after database tables exist
            tag_registry = self.get_service("tag_layer_registry")
            if tag_registry:
                tag_registry.ensure_default_layers()

        self.log_manager.info("Processing contributed commands...")
        for contrib in self.get_contributions("commands"):
            self.command_manager.register(contrib["id"], contrib["class"])

        shell_contribs = self.get_contributions("shell")
        if not shell_contribs:
            self.log_manager.error("No shell was registered. Application cannot start.")
            return

        shell_class = shell_contribs[0]["class"]
        self.shell = shell_class(self, app)

        self._finalize_initialization()

        sys.exit(app.exec())

    def _discover_assets_and_plugins(self, plugins_path):
        asset_dirs = [os.path.join(self.project_root, "assets")]
        plugin_dirs = [(plugins_path, "core")]
        user_plugins_dir = os.path.join(plugins_path, "user")
        if os.path.isdir(user_plugins_dir):
            plugin_dirs.append((user_plugins_dir, "user"))

        self.asset_manager.discover(asset_dirs=asset_dirs, plugin_dirs=plugin_dirs)

    def reload_plugins(self):
        """Performs a full teardown and re-initialization of all plugins."""
        self.log_manager.info("--- Starting Plugin Reload ---")

        if self.shell:
            settings = self.get_service("settings_service")
            if settings:
                settings.set(
                    "window_state", self.shell.saveState().toHex().data().decode()
                )
                panel_states = {}
                for dock_id, dock_widget in self.shell.docks.items():
                    panel = dock_widget.widget()
                    if hasattr(panel, "save_state"):
                        panel_states[dock_id] = panel.save_state()

                if panel_states:
                    settings.set("panel_states", panel_states)

        if self.shell:
            self.shell.clear_all_docks()

        self.plugin_manager.unload_all_plugins()

        self.command_manager.clear()
        self.event_manager.subscribers.clear()
        self.contributions.clear()
        self.template_registry.clear()
        self.graph_registry.clear()
        self.graph_store.clear()
        self.gameplay_runtime.clear()

        persistent = [
            "log_manager",
            "event_manager",
            "service_manager",
            "worker_manager",
            "history_manager",
            "command_manager",
            "asset_manager",
            "template_registry",
            "graph_registry",
            "graph_service",
            "graph_store",
            "gameplay_runtime",
            "framework",
        ]
        self.service_manager.clear_all_except(persistent)

        framework_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(framework_dir)
        plugins_path = os.path.join(project_root, "plugins")

        if plugins_path not in sys.path:
            sys.path.insert(0, plugins_path)
        if self.project_root not in sys.path:
            sys.path.insert(0, self.project_root)

        self.graph_service.load_all()
        self._discover_assets_and_plugins(plugins_path)
        self.plugin_manager.load_plugins()

        db_service = self.get_service("database_service")
        if db_service:
            db_service.create_all_tables()

            # Ensure tag layer defaults are created after database tables exist
            tag_registry = self.get_service("tag_layer_registry")
            if tag_registry:
                tag_registry.ensure_default_layers()

        self._finalize_initialization()

        self.log_manager.info("--- Plugin Reload Finished ---")
        self.log_manager.notification("Plugins reloaded successfully.")

    def _finalize_initialization(self):
        """Shared logic for processing contributions and building the shell UI."""
        self.log_manager.info("Processing contributed commands...")
        for contrib in self.get_contributions("commands"):
            self.command_manager.register(contrib["id"], contrib["class"])

        if self.shell:
            self.shell.build_from_contributions()
            self.shell.show()
        self.event_manager.publish("shell:ready", shell_instance=self.shell)














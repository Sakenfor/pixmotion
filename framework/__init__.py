# story_studio_project/framework/__init__.py
import sys
import os
import importlib.util
import logging
import traceback
from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from interfaces import IPlugin, ICommand, IUndoableCommand


# --- Core Services ---

class LogManager:
    """Handles logging and user-facing notifications."""

    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
        self._notification_callbacks = []

    def info(self, msg, *args, **kwargs):
        logging.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        logging.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        logging.error(msg, *args, **kwargs)

    def debug(self, message):
        """Logs a message with the DEBUG level."""
        self.error(message)

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
    """Discovers plugins from a folder and runs their registration entry point."""
    LOAD_PRIORITY = ['core']

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.loaded_modules = []

    def load_plugins_from_folder(self, folder_path):
        self.log.info(f"Scanning for plugins in '{folder_path}'...")

        plugin_paths = {}
        if not os.path.isdir(folder_path):
            self.log.warning(f"Plugin folder not found at '{folder_path}'. Skipping plugin loading.")
            return

        for name in os.listdir(folder_path):
            plugin_dir = os.path.join(folder_path, name)
            if os.path.isdir(plugin_dir) and os.path.exists(os.path.join(plugin_dir, 'plugin.py')):
                plugin_paths[name] = plugin_dir

        load_order = []
        for plugin_name in self.LOAD_PRIORITY:
            if plugin_name in plugin_paths:
                load_order.append(plugin_name)
        remaining_plugins = sorted([name for name in plugin_paths if name not in load_order])
        load_order.extend(remaining_plugins)
        self.log.info(f"Loading plugins in order: {load_order}")

        for plugin_name in load_order:
            plugin_dir = plugin_paths[plugin_name]
            self._load_plugin(plugin_dir, plugin_name)

    def _load_plugin(self, plugin_dir, plugin_name):
        entry_point = os.path.join(plugin_dir, "plugin.py")
        module_name = f"{plugin_name}.plugin"
        try:
            self.loaded_modules.append(module_name)

            spec = importlib.util.spec_from_file_location(module_name, entry_point)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            plugin_package_name = f"plugins.{plugin_name}"
            for m in list(sys.modules.keys()):
                if m.startswith(plugin_package_name) and m not in self.loaded_modules:
                    self.loaded_modules.append(m)

            if hasattr(module, "Plugin") and issubclass(getattr(module, "Plugin"), IPlugin):
                plugin_instance = getattr(module, "Plugin")()
                plugin_instance.register(self.framework)
                self.log.info(f"Successfully loaded plugin: '{plugin_name}'")
            else:
                self.log.warning(f"Plugin '{plugin_name}' has a 'plugin.py' but no valid 'Plugin' class.")
        except Exception as e:
            self.log.error(f"Failed to load plugin '{plugin_name}': {e}", exc_info=True)

    def unload_all_plugins(self):
        """Attempts to unload all tracked plugin modules from memory."""
        self.log.info(f"Unloading {len(self.loaded_modules)} plugin modules...")
        for module_name in reversed(sorted(self.loaded_modules)):
            if module_name in sys.modules:
                del sys.modules[module_name]
        self.loaded_modules.clear()


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

        self.command_manager = CommandManager(self)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.plugin_manager = PluginManager(self)

        self.service_manager.register("command_manager", self.command_manager)
        self.command_manager.history_manager = self.history_manager

        self.contributions = {}
        self.shell = None

    def get_service(self, service_id):
        return self.service_manager.get(service_id)

    def get_project_root(self):
        return self.project_root

    def register_contribution(self, point, data):
        """
        Registers a contribution from a plugin.
        """
        if point not in self.contributions: self.contributions[point] = []
        self.contributions[point].append(data)
        self.log_manager.info(f"Contribution registered to '{point}': {data.get('id', 'N/A')}")

        if point == "services":
            self.service_manager.register(data['id'], data['instance'])

    def get_contributions(self, point):
        return self.contributions.get(point, [])

    def initialize(self, app):
        """Loads plugins and starts the application shell."""
        framework_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(framework_dir)
        plugins_path = os.path.join(project_root, "plugins")

        sys.path.insert(0, plugins_path)

        self.plugin_manager.load_plugins_from_folder(plugins_path)

        # After all plugins have loaded and registered their models,
        # tell the database service to create all the tables.
        db_service = self.get_service("database_service")
        if db_service:
            db_service.create_all_tables()

        self.log_manager.info("Processing contributed commands...")
        for contrib in self.get_contributions("commands"):
            self.command_manager.register(contrib['id'], contrib['class'])

        shell_contribs = self.get_contributions("shell")
        if not shell_contribs:
            self.log_manager.error("No shell was registered. Application cannot start.")
            return

        shell_class = shell_contribs[0]['class']
        self.shell = shell_class(self, app)

        self._finalize_initialization()

        sys.exit(app.exec())

    def reload_plugins(self):
        """Performs a full teardown and re-initialization of all plugins."""
        self.log_manager.info("--- Starting Plugin Reload ---")

        if self.shell:
            settings = self.get_service("settings_service")
            if settings:
                settings.set("window_state", self.shell.saveState().toHex().data().decode())
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

        persistent = ["log_manager", "event_manager", "service_manager", "worker_manager", "history_manager",
                      "command_manager"]
        self.service_manager.clear_all_except(persistent)

        framework_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(framework_dir)
        plugins_path = os.path.join(project_root, "plugins")

        self.plugin_manager.load_plugins_from_folder(plugins_path)

        # Re-initialize the database with potentially new models
        db_service = self.get_service("database_service")
        if db_service:
            db_service.create_all_tables()

        self._finalize_initialization()

        self.log_manager.info("--- Plugin Reload Finished ---")
        self.log_manager.notification("Plugins reloaded successfully.")

    def _finalize_initialization(self):
        """Shared logic for processing contributions and building the shell UI."""
        self.log_manager.info("Processing contributed commands...")
        for contrib in self.get_contributions("commands"):
            self.command_manager.register(contrib['id'], contrib['class'])

        self.shell.build_from_contributions()

        self.shell.show()
        self.event_manager.publish("shell:ready", shell_instance=self.shell)

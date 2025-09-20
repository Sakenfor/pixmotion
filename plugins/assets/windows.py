# D:/My Drive/code/pixmotion/plugins/assets/windows.py
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTextEdit,
                             QLabel, QSplitter, QHBoxLayout, QStackedWidget)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from core.models import Generation
from .views import ImageViewer


class MediaPreviewWindow(QWidget):
    """A window to preview an asset (image or video) with navigation and metadata."""

    def __init__(self, framework, asset_list, current_index):
        super().__init__()
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.events = framework.get_service("event_manager")
        self.db = framework.get_service("database_service")
        self.asset_list = asset_list
        self.current_index = current_index
        self.creation_prompt = None

        self.setWindowTitle("Asset Preview")
        self.setMinimumSize(800, 600)
        self._init_ui()
        self.load_asset()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        content_splitter = QSplitter(Qt.Orientation.Vertical)

        self.stacked_widget = QStackedWidget()
        self.image_viewer = ImageViewer()
        self.stacked_widget.addWidget(self.image_viewer)
        self.video_widget = QVideoWidget()
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        self.stacked_widget.addWidget(self.video_widget)
        content_splitter.addWidget(self.stacked_widget)

        metadata_widget = QWidget()
        metadata_layout = QVBoxLayout(metadata_widget)
        self.creation_prompt_label = QLabel("Creation Prompt: N/A")
        self.creation_prompt_label.setWordWrap(True)
        self.creation_prompt_label.setStyleSheet("padding: 5px; background-color: #2a2a2a; border-radius: 4px;")
        self.prompt_history_view = QTextEdit()
        self.prompt_history_view.setReadOnly(True)
        metadata_layout.addWidget(self.creation_prompt_label)
        metadata_layout.addWidget(QLabel("Used As Input In:"))
        metadata_layout.addWidget(self.prompt_history_view)
        content_splitter.addWidget(metadata_widget)
        content_splitter.setSizes([400, 200])

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("< Prev")
        self.use_template_btn = QPushButton("Use as Template")
        self.next_btn = QPushButton("Next >")
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.use_template_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)

        main_layout.addWidget(content_splitter)
        main_layout.addLayout(nav_layout)

        self.prev_btn.clicked.connect(self.show_previous)
        self.next_btn.clicked.connect(self.show_next)
        self.use_template_btn.clicked.connect(self._on_use_as_template)

    def load_asset(self):
        asset_data = self.asset_list[self.current_index]
        path = asset_data['path']
        _, ext = os.path.splitext(path.lower())

        if ext in ['.mp4', '.mov', '.avi']:
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.stacked_widget.setCurrentWidget(self.video_widget)
            self.media_player.play()
        else:
            self.media_player.stop()
            self.image_viewer.set_pixmap(QPixmap(path))
            self.stacked_widget.setCurrentWidget(self.image_viewer)

        creation_generations = self.db.query(Generation, lambda g: g.output_asset_id == asset_data['id'])
        if creation_generations:
            self.creation_prompt = creation_generations[0].prompt
            self.creation_prompt_label.setText(f"<b>Creation Prompt:</b> {self.creation_prompt}")
            self.use_template_btn.show()
        else:
            self.creation_prompt = None
            self.creation_prompt_label.setText(f"<b>Source File:</b> {os.path.basename(path)}")
            self.use_template_btn.hide()

        input_generations = self.db.query(Generation, lambda g: (g.input_asset1_id == asset_data['id']) or (g.input_asset2_id == asset_data['id']))
        history_html = "<ul>" + "".join(f"<li>{gen.prompt}</li>" for gen in input_generations) + "</ul>" if input_generations else "Not used as an input yet."
        self.prompt_history_view.setHtml(history_html)

        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.asset_list) - 1)

    def show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_asset()

    def show_next(self):
        if self.current_index < len(self.asset_list) - 1:
            self.current_index += 1
            self.load_asset()

    def closeEvent(self, event):
        self.media_player.stop()
        super().closeEvent(event)

    def _on_use_as_template(self):
        if self.creation_prompt:
            asset_data = self.asset_list[self.current_index]
            self.events.publish("generator:use_template", asset_path=asset_data['path'], prompt=self.creation_prompt)
            self.log.notification(f"Loaded template from '{os.path.basename(asset_data['path'])}'.")
            self.close()
import sys
import os
import json
from typing import List, Dict, Any

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QScrollArea, QLabel,
    QFrame, QSizePolicy, QTextBrowser
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize, QThread, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor

from utils.logger import logger
from agents.orchestrator import OrchestratorAgent

# --- Apple Design System Constants ---
COLOR_BG_LIGHT = "#f5f5f7"
COLOR_BG_DARK = "#000000"
COLOR_TEXT_PRIMARY = "#1d1d1f"
COLOR_TEXT_SECONDARY = "rgba(0, 0, 0, 0.8)"
COLOR_APPLE_BLUE = "#0071e3"
COLOR_DARK_SURFACE = "#272729"
COLOR_WHITE = "#ffffff"

FONT_DISPLAY = "SF Pro Display, Helvetica Neue, Helvetica, Arial, sans-serif"
FONT_TEXT = "SF Pro Text, Helvetica Neue, Helvetica, Arial, sans-serif"

# --- Stylesheet ---
QSS_STYLE = f"""
QMainWindow {{
    background-color: {COLOR_BG_LIGHT};
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

#chatContainer {{
    background-color: {COLOR_BG_LIGHT};
}}

#inputArea {{
    background-color: {COLOR_BG_LIGHT};
    border-top: 1px solid rgba(0, 0, 0, 0.1);
    padding: 20px;
}}

QLineEdit {{
    background-color: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 11px;
    padding: 10px 15px;
    font-family: "{FONT_TEXT}";
    font-size: 17px;
    color: {COLOR_TEXT_PRIMARY};
}}

QLineEdit:focus {{
    border: 2px solid {COLOR_APPLE_BLUE};
}}

QPushButton#sendButton {{
    background-color: {COLOR_APPLE_BLUE};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-family: "{FONT_TEXT}";
    font-size: 17px;
    font-weight: 500;
}}

QPushButton#sendButton:pressed {{
    background-color: #005bb7;
}}

QPushButton#sendButton:disabled {{
    background-color: rgba(0, 113, 227, 0.3);
}}

#messageBubble_user {{
    background-color: {COLOR_APPLE_BLUE};
    border-radius: 18px;
    color: white;
    padding: 12px 16px;
    margin-bottom: 10px;
}}

#messageBubble_assistant {{
    background-color: white;
    border-radius: 18px;
    color: {COLOR_TEXT_PRIMARY};
    padding: 12px 16px;
    margin-bottom: 10px;
    border: 1px solid rgba(0, 0, 0, 0.05);
}}

QLabel {{
    font-family: "{FONT_TEXT}";
    font-size: 16px;
}}

#titleLabel {{
    font-family: "{FONT_DISPLAY}";
    font-size: 18px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
    margin: 10px;
}}
"""

class MessageWidget(QWidget):
    def __init__(self, text, is_user=True):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5)
        
        if is_user:
            self.bubble = QLabel(text)
            self.bubble.setWordWrap(True)
            self.bubble.setObjectName("messageBubble_user")
            layout.addStretch()
            layout.addWidget(self.bubble)
        else:
            # Use QTextBrowser for assistant messages to support basic Markdown/HTML
            self.bubble = QTextBrowser()
            self.bubble.setHtml(text.replace('\n', '<br>')) # Simple replacement, can use a markdown parser if needed
            self.bubble.setOpenExternalLinks(True)
            self.bubble.setReadOnly(True)
            self.bubble.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.bubble.setObjectName("messageBubble_assistant")
            self.bubble.setFrameShape(QFrame.Shape.NoFrame)
            
            # Adjust height based on content
            self.bubble.document().contentsChanged.connect(self.adjust_height)
            
            layout.addWidget(self.bubble)
            layout.addStretch()
            
        # 限制最大宽度
        self.bubble.setFixedWidth(600)

    def adjust_height(self):
        doc_height = self.bubble.document().size().height()
        self.bubble.setFixedHeight(int(doc_height) + 10)

class AgentWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, agent, instruction):
        super().__init__()
        self.agent = agent
        self.instruction = instruction
        
    def run(self):
        try:
            # OrchestratorAgent.process_instruction 是同步调用的（内部使用了 _run_async）
            response = self.agent.process_instruction(self.instruction)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))

class UAVAssistantApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_config()
        self.init_agent()
        self.init_ui()
        
    def load_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = {}

    def init_agent(self):
        self.agent = OrchestratorAgent(self.config)

    def init_ui(self):
        self.setWindowTitle(self.config.get('ui_settings', {}).get('title', 'UAV 综合指挥调度系统'))
        self.showMaximized()
        self.setStyleSheet(QSS_STYLE)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Header ---
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet(f"background-color: white; border-bottom: 1px solid rgba(0, 0, 0, 0.1);")
        header_layout = QHBoxLayout(header)
        
        title = QLabel(self.config.get('ui_settings', {}).get('title', 'UAV 综合指挥调度系统'))
        title.setObjectName("titleLabel")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        main_layout.addWidget(header)
        
        # --- Chat Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.chat_container = QWidget()
        self.chat_container.setObjectName("chatContainer")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()
        self.scroll_area.setWidget(self.chat_container)
        
        main_layout.addWidget(self.scroll_area)
        
        # --- Input Area ---
        input_widget = QWidget()
        input_widget.setObjectName("inputArea")
        input_layout = QHBoxLayout(input_widget)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("请输入调度指令")
        self.input_field.returnPressed.connect(self.send_instruction)
        
        self.send_button = QPushButton("发送")
        self.send_button.setObjectName("sendButton")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self.send_instruction)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        
        main_layout.addWidget(input_widget)
        
        # Add a welcome message
        self.add_message("您好！我是 UAV 综合指挥调度助手。请告诉我您的指令。", is_user=False)

    def add_message(self, text, is_user=True):
        # Remove the stretch at the end
        last_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        
        msg_widget = MessageWidget(text, is_user)
        self.chat_layout.addWidget(msg_widget)
        
        # Add back the stretch
        self.chat_layout.addStretch()
        
        # Scroll to bottom
        # Use QTimer to ensure layout is updated before scrolling
        QTimer.singleShot(50, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def send_instruction(self):
        text = self.input_field.text().strip()
        if not text:
            return
            
        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        
        self.add_message(text, is_user=True)
        
        # Show thinking message
        self.thinking_msg = MessageWidget("调度指挥官正在思考中...", is_user=False)
        last_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        self.chat_layout.addWidget(self.thinking_msg)
        self.chat_layout.addStretch()
        self.scroll_to_bottom()
        
        # Start background worker
        self.worker = AgentWorker(self.agent, text)
        self.worker.finished.connect(self.handle_response)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def handle_response(self, response):
        # Remove thinking message
        self.chat_layout.removeWidget(self.thinking_msg)
        self.thinking_msg.deleteLater()
        
        self.add_message(response, is_user=False)
        
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

    def handle_error(self, error_msg):
        # Remove thinking message
        self.chat_layout.removeWidget(self.thinking_msg)
        self.thinking_msg.deleteLater()
        
        self.add_message(f"执行出错: {error_msg}", is_user=False)
        
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UAVAssistantApp()
    window.show()
    sys.exit(app.exec())

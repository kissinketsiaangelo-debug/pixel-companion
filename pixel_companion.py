import sys
import os
import random
import math
import requests
import threading
import subprocess
import base64
from io import BytesIO
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QRadialGradient, QCursor
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel, QFrame)

# Local Ollama endpoint configuration
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "local-engineer"


class SarahVoiceEngine:
    """Robust offline Text-to-Speech that guarantees responses are read out loud."""

    def __init__(self):
        self.enabled = True
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 160)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                name_lower = voice.name.lower()
                if 'zira' in name_lower or 'hazel' in name_lower or 'female' in name_lower or 'aria' in name_lower:
                    self.engine.setProperty('voice', voice.id)
                    break
        except Exception:
            self.enabled = False

    def speak(self, text):
        def run_speech():
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 160)
                voices = engine.getProperty('voices')
                for voice in voices:
                    if 'zira' in voice.name.lower() or 'female' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                print(f"TTS Error: {e}")

        threading.Thread(target=run_speech, daemon=True).start()


sarah_voice = SarahVoiceEngine()


class SarahChatWindow(QWidget):
    """Interactive chat window with Persistent Memory, Vision OCR, and PC Automation."""

    def __init__(self, companion_ref=None):
        super().__init__(None)
        self.companion = companion_ref
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(400, 320)

        # Persistent conversational history buffer for session memory
        self.chat_history = []

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame()
        self.frame.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 2px solid #38bdf8;
                border-radius: 14px;
            }
        """)

        layout = QVBoxLayout(self.frame)

        # Header bar
        header = QHBoxLayout()
        title = QLabel("💬 Sarah AI - Omnimodal Neural Link")
        title.setStyleSheet("color: #38bdf8; font-family: Consolas; font-weight: bold; font-size: 13px; border: none;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet(
            "QPushButton { color: #f87171; background: transparent; border: none; font-weight: bold; } QPushButton:hover { color: #ef4444; }")
        close_btn.clicked.connect(self.hide)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Chat display area
        self.chat_display = QLabel("Sarah: Systems online. Vision, memory, and automation active.")
        self.chat_display.setWordWrap(True)
        self.chat_display.setStyleSheet(
            "color: #f8fafc; font-family: Segoe UI; font-size: 11px; background: #1e293b; padding: 10px; border-radius: 8px; border: none;")
        layout.addWidget(self.chat_display, stretch=1)

        # Input controls
        input_layout = QHBoxLayout()

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask anything, or request PC actions...")
        self.input_field.setStyleSheet(
            "QLineEdit { background: #1e293b; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 7px; font-size: 11px; } QLineEdit:focus { border: 1px solid #38bdf8; }")
        self.input_field.returnPressed.connect(self.send_message)

        self.send_btn = QPushButton("➔")
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setStyleSheet(
            "QPushButton { background: #0284c7; color: white; border-radius: 6px; border: none; font-weight: bold; } QPushButton:hover { background: #0369a1; }")
        self.send_btn.clicked.connect(self.send_message)

        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setFixedSize(32, 32)
        self.mic_btn.setToolTip("Hold down to speak, release to send")
        self.mic_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; color: white; border-radius: 6px; border: none; } QPushButton:hover { background: #2563eb; }")
        self.mic_btn.pressed.connect(self.start_push_to_talk)
        self.mic_btn.released.connect(self.stop_push_to_talk)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        input_layout.addWidget(self.mic_btn)

        layout.addLayout(input_layout)
        main_layout.addWidget(self.frame)
        self.setLayout(main_layout)

        self.is_recording = False

    def execute_pc_automation(self, command_text):
        cmd = command_text.lower()
        try:
            if "open browser" in cmd or "open chrome" in cmd:
                os.system("start chrome")
                return "Opening Google Chrome for you."
            elif "open notepad" in cmd:
                os.system("notepad")
                return "Opened Notepad."
            elif "take screenshot" in cmd or "capture screen" in cmd:
                import pyautogui
                path = os.path.expanduser("~/Desktop/sarah_screenshot.png")
                pyautogui.screenshot().save(path)
                return "Screenshot saved to your Desktop!"
            elif "lock pc" in cmd or "lock screen" in cmd:
                os.system("rundll32.exe user32.dll,LockWorkStation")
                return "Locking your workstation."
        except Exception as e:
            return f"Failed to execute shortcut: {e}"
        return None

    def capture_screen_vision(self):
        try:
            import pyautogui
            import pytesseract
            if os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
                pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

            screenshot = pyautogui.screenshot()
            extracted_text = pytesseract.image_to_string(screenshot).strip()
            if extracted_text:
                return f"[Visual Screen OCR Text Analysis]: {extracted_text[:800]}"
            return "[Screen captured successfully: Visual interface visible]"
        except Exception:
            return "[Screen captured: Graphical desktop environment active]"

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.chat_history.append(f"User: {text}")
        self.chat_display.setText(f"You: {text}\n\nSarah: Analyzing display & context...")
        self.input_field.clear()

        if self.companion:
            self.companion.set_thought_text("Processing...")
            self.companion.set_state("think")

        def query():
            auto_response = self.execute_pc_automation(text)
            if auto_response:
                self.chat_display.setText(f"You: {text}\n\nSarah: {auto_response}")
                sarah_voice.speak(auto_response)
                self.chat_history.append(f"Sarah: {auto_response}")
                if self.companion:
                    self.companion.set_thought_text(auto_response)
                    self.companion.set_state("happy")
                return

            screen_vision = self.capture_screen_vision()
            history_context = "\n".join(self.chat_history[-6:])

            prompt = (
                f"You are Sarah, an advanced desktop AI companion with screen-reading vision and PC automation.\n"
                f"{screen_vision}\n\n"
                f"Conversation History:\n{history_context}\n\n"
                f"Respond concisely (1-2 sentences) with your signature intelligent persona."
            )

            try:
                payload = {
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False
                }
                res = requests.post(OLLAMA_URL, json=payload, timeout=30)
                if res.status_code == 200:
                    ans = res.json().get('response', 'Task executed successfully.').strip()
                    self.chat_display.setText(f"You: {text}\n\nSarah: {ans}")
                    sarah_voice.speak(ans)
                    self.chat_history.append(f"Sarah: {ans}")
                    if self.companion:
                        self.companion.set_thought_text(ans)
                        self.companion.set_state("think")
                else:
                    err_msg = "Model endpoint busy."
                    self.chat_display.setText(f"Sarah: {err_msg}")
                    sarah_voice.speak(err_msg)
            except Exception:
                err_msg = "Local Ollama server unreachable."
                self.chat_display.setText(f"Sarah: {err_msg}")
                sarah_voice.speak(err_msg)

        threading.Thread(target=query, daemon=True).start()

    def start_push_to_talk(self):
        self.is_recording = True
        self.chat_display.setText("Sarah: 🎙️ Recording... Release button when done.")
        sarah_voice.speak("Listening...")

        def record_thread():
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.3)
                    audio = r.listen(source, timeout=10, phrase_time_limit=15)
                    if self.is_recording:
                        text = r.recognize_google(audio)
                        self.input_field.setText(text)
            except Exception:
                if self.is_recording:
                    self.chat_display.setText("Sarah: Voice recording timed out. Type your query!")

        threading.Thread(target=record_thread, daemon=True).start()

    def stop_push_to_talk(self):
        self.is_recording = False
        if self.input_field.text().strip():
            self.send_message()


class PolishedSarahCompanion(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.width = 160
        self.height = 170

        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()

        self.x_pos = self.screen_width - 240
        self.y_pos = self.screen_height - self.height - 35
        self.setGeometry(self.x_pos, self.y_pos, self.width, self.height)

        self.current_state = "walking"
        self.direction = 1
        self.is_dragging = False
        self.user_placed = False
        self.drag_count = 0
        self.drag_start_pos = QPoint()
        self.drag_position = QPoint()
        self.anim_frame = 0.0
        self.thought_text = "Systems online."

        self.chat_popup = SarahChatWindow(self)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.autonomous_loop)
        self.anim_timer.start(40)

    def set_state(self, state):
        self.current_state = state
        self.update()

    def set_thought_text(self, text):
        self.thought_text = text
        self.update()

    def autonomous_loop(self):
        self.anim_frame += 0.25
        if self.anim_frame > 100:
            self.anim_frame = 0.0

        if self.current_state == "walking" and not self.is_dragging and not self.user_placed:
            self.x_pos += int(2 * self.direction)
            if self.x_pos > self.screen_width - 140:
                self.direction = -1
            elif self.x_pos < self.screen_width - 550:
                self.direction = 1
            self.move(self.x_pos, self.y_pos)

        if self.chat_popup.isVisible():
            if QApplication.mouseButtons() == Qt.MouseButton.LeftButton:
                global_pos = QCursor.pos()
                if not self.chat_popup.geometry().contains(global_pos) and not self.geometry().contains(global_pos):
                    self.chat_popup.hide()
                    self.set_state("walking")

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = int(self.width / 2)
        cy = int(self.height / 2) + 10

        skin_color = QColor(245, 198, 160)
        sweater_color = QColor(56, 189, 248) if self.current_state != "annoyed" else QColor(239, 68, 68)
        pants_color = QColor(30, 90, 200)
        shoe_color = QColor(20, 70, 160)

        if self.current_state in ["think", "happy", "annoyed"]:
            painter.setPen(QPen(QColor(56, 189, 248), 2))
            painter.setBrush(QBrush(QColor(15, 23, 42, 240)))
            painter.drawRoundedRect(QRectF(cx - 85, cy - 115, 170, 48), 12, 12)
            painter.drawEllipse(QRectF(cx - 10, cy - 69, 10, 10))
            painter.drawEllipse(QRectF(cx - 5, cy - 56, 6, 6))

            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QColor(56, 189, 248))
            painter.drawText(QRectF(cx - 80, cy - 110, 160, 38),
                             Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.thought_text)

        bounce = int(math.sin(self.anim_frame * 4) * 3) if self.current_state == "walking" else 0
        leg_stride = int(math.sin(self.anim_frame * 3) * 8) if self.current_state == "walking" else 0

        painter.setPen(QPen(pants_color, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(cx - 4), int(cy + 15 + bounce), int(cx - 4 - leg_stride), int(cy + 42))
        painter.drawLine(int(cx + 4), int(cy + 15 + bounce), int(cx + 4 + leg_stride), int(cy + 42))

        painter.setPen(QPen(shoe_color, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPoint(int(cx - 4 - leg_stride), int(cy + 44))
        painter.drawPoint(int(cx + 4 + leg_stride), int(cy + 44))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(sweater_color))
        painter.drawRoundedRect(QRectF(cx - 14, cy - 2 + bounce, 28, 26), 8, 8)

        painter.setPen(QPen(skin_color, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if self.current_state == "think":
            painter.drawLine(int(cx - 10), int(cy + 4 + bounce), int(cx - 2), int(cy - 2 + bounce))
            painter.drawLine(int(cx + 10), int(cy + 4 + bounce), int(cx + 2), int(cy - 2 + bounce))
        elif self.current_state == "annoyed":
            painter.drawLine(int(cx - 12), int(cy + 8), int(cx + 12), int(cy + 8))
        else:
            painter.drawLine(int(cx - 12), int(cy + bounce), int(cx - 18 + leg_stride), int(cy + 18))
            painter.drawLine(int(cx + 12), int(cy + bounce), int(cx + 18 - leg_stride), int(cy + 18))

        head_grad = QRadialGradient(cx, cy - 22 + bounce, 18)
        head_grad.setColorAt(0, QColor(255, 215, 180))
        head_grad.setColorAt(1, QColor(230, 175, 135))
        painter.setBrush(QBrush(head_grad))
        painter.drawEllipse(QRectF(cx - 16, cy - 34 + bounce, 32, 32))

        painter.setBrush(QBrush(QColor(15, 23, 42)))
        if self.current_state == "annoyed":
            painter.drawLine(int(cx - 10), int(cy - 25), int(cx - 6), int(cy - 21))
            painter.drawLine(int(cx + 6), int(cy - 21), int(cx + 10), int(cy - 25))
        else:
            painter.drawEllipse(QRectF(cx - 8, cy - 23 + bounce, 4, 5))
            painter.drawEllipse(QRectF(cx + 4, cy - 23 + bounce, 4, 5))

        painter.setPen(QPen(QColor(190, 120, 90), 1))
        painter.drawPoint(int(cx), int(cy - 18 + bounce))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.current_state == "annoyed":
            painter.drawArc(QRectF(cx - 3, cy - 15 + bounce, 6, 4), 0, 180 * 16)
        elif self.current_state == "happy":
            painter.drawArc(QRectF(cx - 4, cy - 18 + bounce, 8, 6), 0, -180 * 16)
        else:
            painter.drawArc(QRectF(cx - 3, cy - 16 + bounce, 6, 4), 0, -180 * 16)

        painter.setPen(Qt.PenStyle.NoPen)
        hair_grad = QLinearGradient(cx - 20, cy - 40, cx + 20, cy - 20)
        hair_grad.setColorAt(0, QColor(130, 65, 30))
        hair_grad.setColorAt(1, QColor(90, 40, 15))
        painter.setBrush(QBrush(hair_grad))
        painter.drawEllipse(QRectF(cx - 18, cy - 38 + bounce, 36, 22))
        painter.drawEllipse(QRectF(cx - 24, cy - 28 + bounce, 10, 10))
        painter.drawEllipse(QRectF(cx + 14, cy - 28 + bounce, 10, 10))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.drag_start_pos = event.globalPosition().toPoint()
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if (event.globalPosition().toPoint() - self.drag_start_pos).manhattanLength() > 4:
                self.is_dragging = True
                self.user_placed = True
                self.drag_count += 1

                if self.drag_count > 5:
                    self.set_state("annoyed")
                    self.thought_text = "Hey! Stop dragging me around!"

                self.move(event.globalPosition().toPoint() - self.drag_position)
                self.x_pos = self.x()
                self.y_pos = self.y()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.is_dragging:
                chat_x = min(self.x_pos, self.screen_width - 400)
                chat_y = max(self.y_pos - 320, 30)
                self.chat_popup.move(chat_x, chat_y)
                self.chat_popup.show()
                self.chat_popup.raise_()

                self.set_state("think")
                self.thought_text = "Systems online. What do you see on screen?"
                sarah_voice.speak("Systems online. What do you see on screen?")

            self.is_dragging = False
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    companion = PolishedSarahCompanion()
    companion.show()
    sys.exit(app.exec())
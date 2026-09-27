"""
LoginPage for PySide6 GUI.
Provides student authentication with salted hashing via AuthService.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from core.auth import AuthService


class LoginPage(QWidget):
    """
    Login and account creation view.
    """

    login_successful = Signal(dict)  # Emits user data dictionary

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setProperty("class", "card")
        card.setFixedWidth(400)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        title = QLabel("Smart Course Planner")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #38BDF8;")
        card_layout.addWidget(title)

        subtitle = QLabel("Student Course Planning & Registration Optimization")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #94A3B8; font-size: 12px; margin-bottom: 8px;")
        card_layout.addWidget(subtitle)

        # Username
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username (e.g. student)")
        card_layout.addWidget(QLabel("Username"))
        card_layout.addWidget(self.user_input)

        # Password
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(QLabel("Password"))
        card_layout.addWidget(self.pass_input)

        # Buttons
        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("Sign In")
        self.login_btn.clicked.connect(self._handle_login)

        self.register_btn = QPushButton("Register New")
        self.register_btn.setStyleSheet("background-color: #334155; color: #F8FAFC;")
        self.register_btn.clicked.connect(self._handle_register)

        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        card_layout.addLayout(btn_layout)

        # Default hint
        hint = QLabel("Demo account: student / pass123")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #64748B; font-size: 11px; margin-top: 6px;")
        card_layout.addWidget(hint)

        layout.addWidget(card)

    def _handle_login(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both username and password.")
            return

        success, user_data, msg = self.auth_service.login(username, password)
        if success and user_data:
            self.login_successful.emit(user_data)
        else:
            QMessageBox.warning(self, "Authentication Failed", msg)

    def _handle_register(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Registration Error", "Please fill in username and password.")
            return

        success, msg = self.auth_service.register(username, password, full_name=username.title())
        if success:
            QMessageBox.information(self, "Registered", "Account created successfully! You may now sign in.")
        else:
            QMessageBox.warning(self, "Registration Failed", msg)

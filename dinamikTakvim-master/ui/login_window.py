from PyQt5.QtWidgets import (QDialog, QLineEdit, QPushButton, QVBoxLayout,
                             QLabel, QMessageBox, QFormLayout)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

# Veritabanı fonksiyonlarımızı içe aktarıyoruz.
from database import verify_user


class LoginWindow(QDialog):
    # Başarılı giriş sonrası tetiklenecek sinyal.
    # Kullanıcının bilgilerini (sözlük olarak) ana uygulamaya gönderir.
    login_success = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dinamik Sınav Takvimi Sistemi - Giriş")
        self.setGeometry(400, 400, 400, 220)
        self.init_ui()

    def init_ui(self):
        # Düzenli bir form görünümü için QFormLayout kullanıyoruz.
        layout = QFormLayout()
        layout.setSpacing(15)

        # Pencere başlığı
        title_label = QLabel("Sisteme Giriş Yapınız")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("ornek@kocaeli.edu.tr")
        self.email_input.setFont(QFont("Arial", 10))

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setEchoMode(QLineEdit.Password)  # Şifreyi gizler
        self.password_input.setFont(QFont("Arial", 10))

        # Enter tuşuna basıldığında giriş yapmayı tetikle
        self.password_input.returnPressed.connect(self.handle_login)

        self.login_button = QPushButton("Giriş Yap")
        self.login_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.login_button.clicked.connect(self.handle_login)

        # Arayüz elemanlarını layout'a ekle
        layout.addRow(title_label)
        layout.addRow("E-posta:", self.email_input)
        layout.addRow("Şifre:", self.password_input)
        layout.addRow(self.login_button)

        self.setLayout(layout)

    def handle_login(self):
        """'Giriş Yap' butonuna basıldığında veya Enter'a basıldığında çalışır."""
        email = self.email_input.text().strip()
        password = self.password_input.text()

        # Alanların boş olup olmadığını kontrol et
        if not email or not password:
            QMessageBox.warning(self, "Eksik Bilgi", "E-posta ve şifre alanları boş bırakılamaz.")
            return

        # Veritabanından kullanıcıyı doğrula
        user_data = verify_user(email, password)

        if user_data:
            # Kullanıcı bilgileri doğruysa
            # Başarı sinyalini, kullanıcı verileriyle birlikte gönder.
            self.login_success.emit(user_data)
        else:
            # Kullanıcı bilgileri yanlışsa
            QMessageBox.warning(self, "Giriş Başarısız", "Hatalı e-posta veya şifre girdiniz.")


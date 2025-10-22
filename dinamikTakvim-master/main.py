import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.login_window import LoginWindow
from ui.admin_dashboard import AdminDashboard
from ui.coordinator_dashboard import CoordinatorDashboard


class ApplicationController:
    """
    Uygulamanın ana kontrolcüsü. Pencereleri yönetir ve aralarındaki
    geçişi sağlar.
    """

    def __init__(self):
        # Uygulama başladığında ilk olarak Login penceresini oluştur ve göster.
        self.login_window = LoginWindow()

        # Login penceresinden 'login_success' sinyali geldiğinde,
        # 'show_dashboard' metodunu çalıştır.
        self.login_window.login_success.connect(self.show_dashboard)
        self.login_window.show()

        # Açılacak olan ana panel penceresini tutmak için bir referans.
        # Bu, pencerenin çöp toplayıcı tarafından silinmesini engeller.
        self.main_window = None

    def show_dashboard(self, user_data):
        """
        Başarılı bir giriş işleminden sonra ilgili rolün panelini gösterir.
        Giriş penceresini kapatır.
        """
        role = user_data.get('role')

        # Giriş penceresini kapatıyoruz.
        self.login_window.close()

        if role == 'admin':
            # Admin rolü için AdminDashboard'u oluştur ve göster.
            self.main_window = AdminDashboard(user_data)
            self.main_window.logout_signal.connect(self.handle_logout)
            self.main_window.show()
        elif role == 'coordinator':
            # Coordinator rolü için CoordinatorDashboard'u oluştur ve göster.
            self.main_window = CoordinatorDashboard(user_data)
            self.main_window.logout_signal.connect(self.handle_logout)
            self.main_window.show()
        else:
            # Geçersiz bir rol gelmesi durumunda kritik bir hata mesajı göster.
            # Normalde bu durumun oluşmaması gerekir.
            QMessageBox.critical(None, "Sistem Hatası", "Geçersiz kullanıcı rolü tespit edildi!")
    
    def handle_logout(self):
        """Çıkış yapıldığında çağrılır, giriş ekranına döner."""
        # Mevcut dashboard'u kapat
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        
        # Yeni login penceresi oluştur
        self.login_window = LoginWindow()
        self.login_window.login_success.connect(self.show_dashboard)
        self.login_window.show()


def main():
    """Ana uygulama fonksiyonu."""
    app = QApplication(sys.argv)

    # ApplicationController'ı başlat.
    # Bu, login ekranını gösterecek ve kullanıcıya uygun paneli yönlendirecek.
    controller = ApplicationController()

    # Uygulamanın olay döngüsünü başlat.
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


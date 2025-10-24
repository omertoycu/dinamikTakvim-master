import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.login_window import LoginWindow
from ui.admin_dashboard import AdminDashboard
from ui.coordinator_dashboard import CoordinatorDashboard


def initialize_admin_password():
    """İlk kurulumda admin şifresini hash'ler."""
    from database import get_db_connection
    from password_utils import hash_password, verify_password
    
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, password FROM users WHERE email = 'admin@kocaeli.edu.tr' AND role = 'admin'")
        admin = cursor.fetchone()
        
        if admin:
            stored_password = admin['password']
            # Eğer şifre düz metin ise (admin123), hash'le
            if stored_password == 'admin123':
                hashed = hash_password('admin123')
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, admin['id']))
                connection.commit()
                print("Admin şifresi güvenli hale getirildi.")
            # Eğer şifre hash'li ama geçerli değilse (eski format), yeniden hash'le
            elif ':' not in stored_password or not verify_password('admin123', stored_password):
                hashed = hash_password('admin123')
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, admin['id']))
                connection.commit()
                print("Admin şifresi yenilendi.")
    except Exception as e:
        print(f"Admin şifresi güncellenirken hata: {e}")
    finally:
        cursor.close()
        connection.close()


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
    
    # İlk başlatmada admin şifresini kontrol et ve hash'le
    initialize_admin_password()

    # ApplicationController'ı başlat.
    # Bu, login ekranını gösterecek ve kullanıcıya uygun paneli yönlendirecek.
    controller = ApplicationController()

    # Uygulamanın olay döngüsünü başlat.
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()




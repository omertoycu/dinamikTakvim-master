from PyQt5.QtWidgets import (QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QComboBox, QMessageBox, QFormLayout,
                             QHeaderView, QToolBar, QAction, QSizePolicy)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal

# Gerekli veritabanı fonksiyonlarını içe aktar
from database import get_all_departments, get_all_users, add_new_user


class AdminDashboard(QMainWindow):
    """Admin paneli ana penceresi."""
    
    # Çıkış yapıldığında sinyal gönder
    logout_signal = pyqtSignal()

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.setWindowTitle("Admin Paneli - Dinamik Sınav Takvimi Sistemi")
        self.setGeometry(200, 200, 950, 600)
        
        # Toolbar oluştur
        self.create_toolbar()

        # Ana widget olarak bir QTabWidget (Sekmeli arayüz) oluştur
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Sekmeleri oluştur
        self.user_management_tab = QWidget()
        self.departments_view_tab = QWidget()
        self.classrooms_view_tab = QWidget()
        self.courses_view_tab = QWidget()
        self.exams_view_tab = QWidget()

        self.tabs.addTab(self.user_management_tab, "Kullanıcı Yönetimi")
        self.tabs.addTab(self.departments_view_tab, "Bölümler")
        self.tabs.addTab(self.classrooms_view_tab, "Derslikler")
        self.tabs.addTab(self.courses_view_tab, "Dersler")
        self.tabs.addTab(self.exams_view_tab, "Sınavlar")

        # Sekmelerin iç arayüzlerini oluşturan fonksiyonları çağır
        self.init_user_management_ui()
        self.init_departments_view_ui()
        self.init_classrooms_view_ui()
        self.init_courses_view_ui()
        self.init_exams_view_ui()
    
    def create_toolbar(self):
        """Üst toolbar'ı oluşturur (logout butonu için)."""
        toolbar = QToolBar("Ana Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Kullanıcı bilgisi
        user_label = QLabel(f"  👤 {self.user_data.get('email', 'Admin')} (Admin)  ")
        user_label.setStyleSheet("font-weight: bold; color: #e74c3c; padding: 5px;")
        toolbar.addWidget(user_label)
        
        toolbar.addSeparator()
        
        # Spacer ekle (sağa yaslamak için)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar.addWidget(spacer)
        
        # Logout butonu
        logout_action = QAction("🚪 Çıkış Yap", self)
        logout_action.setStatusTip("Sistemden çıkış yap")
        logout_action.triggered.connect(self.handle_logout)
        logout_action.setShortcut("Ctrl+Q")
        toolbar.addAction(logout_action)
    
    def handle_logout(self):
        """Çıkış yapma işlemini yönetir."""
        reply = QMessageBox.question(
            self, 
            'Çıkış Onayı',
            "Sistemden çıkmak istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.logout_signal.emit()
            self.close()

    def init_user_management_ui(self):
        """Kullanıcı yönetimi sekmesinin arayüzünü oluşturur."""
        # Ana layout: Sol (form) ve Sağ (tablo) olarak ikiye ayrılır
        main_layout = QHBoxLayout()

        # --- Sol Taraf: Yeni Kullanıcı Ekleme Formu ---
        form_container = QWidget()
        form_layout = QFormLayout()
        form_container.setLayout(form_layout)

        form_title = QLabel("Yeni Kullanıcı Ekle")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        form_title.setFont(font)

        self.email_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.role_combobox = QComboBox()
        self.role_combobox.addItems(["coordinator", "admin"])

        self.department_combobox = QComboBox()
        # İlk eleman placeholder olarak görev yapar, 'userData'sı -1'dir.
        self.department_combobox.addItem("Bölüm Seçiniz...", -1)
        self.load_departments_into_combobox()

        # Rol "admin" seçildiğinde bölüm seçimi pasif hale gelir
        self.role_combobox.currentTextChanged.connect(self.toggle_department_selection)

        add_user_button = QPushButton("Kullanıcıyı Ekle")
        add_user_button.clicked.connect(self.handle_add_user)

        # Form elemanlarını layout'a ekle
        form_layout.addRow(form_title)
        form_layout.addRow("E-posta:", self.email_input)
        form_layout.addRow("Şifre:", self.password_input)
        form_layout.addRow("Rol:", self.role_combobox)
        form_layout.addRow("Bölüm:", self.department_combobox)
        form_layout.addRow(add_user_button)

        # --- Sağ Taraf: Mevcut Kullanıcılar Tablosu ---
        table_container = QWidget()
        table_layout = QVBoxLayout()
        table_container.setLayout(table_layout)

        table_title = QLabel("Mevcut Kullanıcılar")
        table_title.setFont(font)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["ID", "E-posta", "Rol", "Bölüm"])
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Tabloyu sadece okunabilir yap
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Sütunları genişlet

        table_layout.addWidget(table_title)
        table_layout.addWidget(self.users_table)

        # Oluşturulan sol ve sağ bölümleri ana layout'a ekle
        main_layout.addWidget(form_container, 1)  # Form, pencerenin 1/3'ünü kaplasın
        main_layout.addWidget(table_container, 2)  # Tablo, pencerenin 2/3'ünü kaplasın

        self.user_management_tab.setLayout(main_layout)

        self.load_users_into_table()  # Başlangıçta kullanıcıları tabloya yükle

    def load_departments_into_combobox(self):
        """Veritabanından bölümleri alıp combobox'a ekler."""
        departments = get_all_departments()
        for dept in departments:
            self.department_combobox.addItem(dept['name'], dept['id'])

    def load_users_into_table(self):
        """Veritabanından tüm kullanıcıları alıp tabloya yükler."""
        self.users_table.setRowCount(0)  # Her yüklemeden önce tabloyu temizle
        users = get_all_users()
        for row_num, user in enumerate(users):
            self.users_table.insertRow(row_num)
            self.users_table.setItem(row_num, 0, QTableWidgetItem(str(user['id'])))
            self.users_table.setItem(row_num, 1, QTableWidgetItem(user['email']))
            self.users_table.setItem(row_num, 2, QTableWidgetItem(user['role']))
            # Admin'in bölümü olmayabilir (NULL), bu yüzden None kontrolü yapılır.
            department_name = user['department_name'] if user['department_name'] else "N/A"
            self.users_table.setItem(row_num, 3, QTableWidgetItem(department_name))

    def toggle_department_selection(self, role):
        """Rol 'admin' olarak seçilirse bölüm seçeneğini devre dışı bırakır."""
        if role == 'admin':
            self.department_combobox.setEnabled(False)
            self.department_combobox.setCurrentIndex(0)
        else:
            self.department_combobox.setEnabled(True)

    def handle_add_user(self):
        """'Kullanıcıyı Ekle' butonuna tıklandığında çalışır."""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        role = self.role_combobox.currentText()
        department_id = self.department_combobox.currentData()

        if not email or not password:
            QMessageBox.warning(self, "Eksik Bilgi", "E-posta ve şifre alanları boş bırakılamaz.")
            return

        if role == 'coordinator' and department_id == -1:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen koordinatör için bir bölüm seçiniz.")
            return

        success, message = add_new_user(email, password, role, department_id)

        if success:
            QMessageBox.information(self, "Başarılı", message)
            self.load_users_into_table()  # Yeni kullanıcı eklendiği için tabloyu yenile
            # Formu temizle
            self.email_input.clear()
            self.password_input.clear()
        else:
            QMessageBox.critical(self, "Hata", message)

    def init_departments_view_ui(self):
        """Bölümler görüntüleme sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Bölümler")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Yenile butonu
        refresh_button = QPushButton("Yenile")
        refresh_button.clicked.connect(self.load_departments_into_table)
        
        # Bölümler tablosu
        self.departments_table = QTableWidget()
        self.departments_table.setColumnCount(2)
        self.departments_table.setHorizontalHeaderLabels(["ID", "Bölüm Adı"])
        self.departments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.departments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(title)
        layout.addWidget(refresh_button)
        layout.addWidget(self.departments_table)
        
        self.departments_view_tab.setLayout(layout)
        self.load_departments_into_table()

    def init_classrooms_view_ui(self):
        """Derslikler görüntüleme sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Tüm Derslikler")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Yenile butonu
        refresh_button = QPushButton("Yenile")
        refresh_button.clicked.connect(self.load_all_classrooms_into_table)
        
        # Derslikler tablosu
        self.all_classrooms_table = QTableWidget()
        self.all_classrooms_table.setColumnCount(6)
        self.all_classrooms_table.setHorizontalHeaderLabels([
            "ID", "Bölüm", "Kod", "Ad", "Kapasite", "Sıra Yapısı"
        ])
        self.all_classrooms_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.all_classrooms_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(title)
        layout.addWidget(refresh_button)
        layout.addWidget(self.all_classrooms_table)
        
        self.classrooms_view_tab.setLayout(layout)
        self.load_all_classrooms_into_table()

    def init_courses_view_ui(self):
        """Dersler görüntüleme sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Tüm Dersler")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Yenile butonu
        refresh_button = QPushButton("Yenile")
        refresh_button.clicked.connect(self.load_all_courses_into_table)
        
        # Dersler tablosu
        self.all_courses_table = QTableWidget()
        self.all_courses_table.setColumnCount(7)
        self.all_courses_table.setHorizontalHeaderLabels([
            "ID", "Bölüm", "Kod", "Ad", "Tür", "Sınıf", "Öğretim Üyesi"
        ])
        self.all_courses_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.all_courses_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(title)
        layout.addWidget(refresh_button)
        layout.addWidget(self.all_courses_table)
        
        self.courses_view_tab.setLayout(layout)
        self.load_all_courses_into_table()

    def init_exams_view_ui(self):
        """Sınavlar görüntüleme sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Tüm Sınavlar")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Yenile butonu
        refresh_button = QPushButton("Yenile")
        refresh_button.clicked.connect(self.load_all_exams_into_table)
        
        # Sınavlar tablosu
        self.all_exams_table = QTableWidget()
        self.all_exams_table.setColumnCount(8)
        self.all_exams_table.setHorizontalHeaderLabels([
            "ID", "Bölüm", "Ders Kodu", "Sınav Türü", "Tarih", "Saat", "Öğretim Üyesi", "Derslikler"
        ])
        self.all_exams_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.all_exams_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(title)
        layout.addWidget(refresh_button)
        layout.addWidget(self.all_exams_table)
        
        self.exams_view_tab.setLayout(layout)
        self.load_all_exams_into_table()

    def load_departments_into_table(self):
        """Bölümleri tabloya yükler."""
        from database import get_all_departments
        
        self.departments_table.setRowCount(0)
        departments = get_all_departments()
        
        for row_num, dept in enumerate(departments):
            self.departments_table.insertRow(row_num)
            self.departments_table.setItem(row_num, 0, QTableWidgetItem(str(dept['id'])))
            self.departments_table.setItem(row_num, 1, QTableWidgetItem(dept['name']))

    def load_all_classrooms_into_table(self):
        """Tüm derslikleri tabloya yükler."""
        from database import get_db_connection
        
        self.all_classrooms_table.setRowCount(0)
        connection = get_db_connection()
        if not connection:
            return
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT cl.id, d.name as department_name, cl.code, cl.name, 
                       cl.capacity, cl.seating_type
                FROM classrooms cl
                JOIN departments d ON cl.department_id = d.id
                ORDER BY d.name, cl.code
            """
            cursor.execute(query)
            classrooms = cursor.fetchall()
            
            for row_num, classroom in enumerate(classrooms):
                self.all_classrooms_table.insertRow(row_num)
                self.all_classrooms_table.setItem(row_num, 0, QTableWidgetItem(str(classroom['id'])))
                self.all_classrooms_table.setItem(row_num, 1, QTableWidgetItem(classroom['department_name']))
                self.all_classrooms_table.setItem(row_num, 2, QTableWidgetItem(classroom['code']))
                self.all_classrooms_table.setItem(row_num, 3, QTableWidgetItem(classroom['name']))
                self.all_classrooms_table.setItem(row_num, 4, QTableWidgetItem(str(classroom['capacity'])))
                self.all_classrooms_table.setItem(row_num, 5, QTableWidgetItem(str(classroom['seating_type'])))
                
        except Exception as e:
            print(f"Derslikler yüklenirken hata: {e}")
        finally:
            connection.close()

    def load_all_courses_into_table(self):
        """Tüm dersleri tabloya yükler."""
        from database import get_db_connection
        
        self.all_courses_table.setRowCount(0)
        connection = get_db_connection()
        if not connection:
            return
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT c.id, d.name as department_name, c.code, c.name, 
                       c.course_type, c.class_level, i.full_name as instructor_name
                FROM courses c
                JOIN departments d ON c.department_id = d.id
                JOIN instructors i ON c.instructor_id = i.id
                ORDER BY d.name, c.code
            """
            cursor.execute(query)
            courses = cursor.fetchall()
            
            for row_num, course in enumerate(courses):
                self.all_courses_table.insertRow(row_num)
                self.all_courses_table.setItem(row_num, 0, QTableWidgetItem(str(course['id'])))
                self.all_courses_table.setItem(row_num, 1, QTableWidgetItem(course['department_name']))
                self.all_courses_table.setItem(row_num, 2, QTableWidgetItem(course['code']))
                self.all_courses_table.setItem(row_num, 3, QTableWidgetItem(course['name']))
                self.all_courses_table.setItem(row_num, 4, QTableWidgetItem(course['course_type']))
                self.all_courses_table.setItem(row_num, 5, QTableWidgetItem(str(course['class_level'])))
                self.all_courses_table.setItem(row_num, 6, QTableWidgetItem(course['instructor_name']))
                
        except Exception as e:
            print(f"Dersler yüklenirken hata: {e}")
        finally:
            connection.close()

    def load_all_exams_into_table(self):
        """Tüm sınavları tabloya yükler."""
        from database import get_db_connection
        
        self.all_exams_table.setRowCount(0)
        connection = get_db_connection()
        if not connection:
            return
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT e.id, d.name as department_name, c.code as course_code,
                       e.exam_type, e.exam_date, e.start_time, i.full_name as instructor_name,
                       GROUP_CONCAT(cl.code SEPARATOR ', ') as classrooms
                FROM exams e
                JOIN courses c ON e.course_id = c.id
                JOIN departments d ON c.department_id = d.id
                JOIN instructors i ON c.instructor_id = i.id
                LEFT JOIN exam_assignments ea ON e.id = ea.exam_id
                LEFT JOIN classrooms cl ON ea.classroom_id = cl.id
                GROUP BY e.id, d.name, c.code, e.exam_type, e.exam_date, e.start_time, i.full_name
                ORDER BY e.exam_date, e.start_time
            """
            cursor.execute(query)
            exams = cursor.fetchall()
            
            for row_num, exam in enumerate(exams):
                self.all_exams_table.insertRow(row_num)
                self.all_exams_table.setItem(row_num, 0, QTableWidgetItem(str(exam['id'])))
                self.all_exams_table.setItem(row_num, 1, QTableWidgetItem(exam['department_name']))
                self.all_exams_table.setItem(row_num, 2, QTableWidgetItem(exam['course_code']))
                self.all_exams_table.setItem(row_num, 3, QTableWidgetItem(exam['exam_type']))
                self.all_exams_table.setItem(row_num, 4, QTableWidgetItem(exam['exam_date'].strftime('%d.%m.%Y')))
                self.all_exams_table.setItem(row_num, 5, QTableWidgetItem(exam['start_time'].strftime('%H:%M')))
                self.all_exams_table.setItem(row_num, 6, QTableWidgetItem(exam['instructor_name']))
                self.all_exams_table.setItem(row_num, 7, QTableWidgetItem(exam['classrooms'] or 'Atanmamış'))
                
        except Exception as e:
            print(f"Sınavlar yüklenirken hata: {e}")
        finally:
            connection.close()


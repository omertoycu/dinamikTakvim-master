# ui/coordinator_dashboard.py
# Bölüm Koordinatörü paneli arayüzünü ve derslik yönetimi işlevlerini içerir.

from PyQt5.QtWidgets import (QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QComboBox, QMessageBox, QFormLayout,
                             QHeaderView, QSpinBox, QDialog, QGridLayout, QFileDialog,
                             QProgressBar, QTextEdit, QDateEdit, QCheckBox, QToolBar, QAction)
from PyQt5.QtGui import QFont, QColor, QIcon
from PyQt5.QtCore import Qt, QDate, QObject, QThread, pyqtSignal
from datetime import datetime, timedelta
# import pandas as pd  # Geçici olarak devre dışı

# Gerekli veritabanı fonksiyonlarını içe aktar
from database import (get_classrooms_by_department, add_classroom,
                      update_classroom, delete_classroom, get_classroom_details, get_db_connection, sanitize_courses)
from excel_processor import process_courses_excel, process_students_excel


class ExcelWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, mode, file_path, department_id=None):
        super().__init__()
        self.mode = mode  # 'courses' or 'students'
        self.file_path = file_path
        self.department_id = department_id

    def run(self):
        try:
            if self.mode == 'courses':
                results = process_courses_excel(self.file_path, self.department_id)
            else:
                results = process_students_excel(self.file_path)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
from exam_scheduler import ExamScheduler
from seating_planner import SeatingPlanner
from export_manager import ExportManager


class CoordinatorDashboard(QMainWindow):
    """Bölüm Koordinatörü paneli ana penceresi."""
    
    # Çıkış yapıldığında sinyal gönder
    logout_signal = pyqtSignal()

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.department_id = self.user_data['department_id']
        # Seçili olan dersliğin ID'sini tutmak için
        self.selected_classroom_id = None

        self.setWindowTitle(f"Bölüm Koordinatör Paneli - {self.user_data.get('department_name', '')}")
        self.setGeometry(200, 200, 1100, 700)
        
        # Toolbar oluştur
        self.create_toolbar()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Sekmeleri oluştur
        self.classroom_tab = QWidget()
        self.course_upload_tab = QWidget()
        self.student_upload_tab = QWidget()
        self.exam_schedule_tab = QWidget()
        self.seating_plan_tab = QWidget()
        self.schedule_view_tab = QWidget()
        self.export_tab = QWidget()
        self.student_list_tab = QWidget()
        self.course_list_tab = QWidget()

        self.tabs.addTab(self.classroom_tab, "Derslik Yönetimi")
        self.tabs.addTab(self.course_upload_tab, "Ders Listesi Yükle")
        self.tabs.addTab(self.student_upload_tab, "Öğrenci Listesi Yükle")
        self.tabs.addTab(self.student_list_tab, "Öğrenci Listesi")
        self.tabs.addTab(self.course_list_tab, "Ders Listesi")
        self.tabs.addTab(self.exam_schedule_tab, "Sınav Zamanlama")
        self.tabs.addTab(self.seating_plan_tab, "Oturma Planı")
        self.tabs.addTab(self.schedule_view_tab, "Program Görünümü")
        self.tabs.addTab(self.export_tab, "Dışa Aktarma")

        # Proje tanımına göre derslikler girilmeden diğer tablar pasif olmalı
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)
        self.tabs.setTabEnabled(4, False)
        self.tabs.setTabEnabled(5, False)

        self.init_classroom_ui()
        self.init_course_upload_ui()
        self.init_student_upload_ui()
        self.init_student_list_ui()
        self.init_course_list_ui()
        self.init_exam_schedule_ui()
        self.init_seating_plan_ui()
        self.init_schedule_view_ui()
        self.init_export_ui()
    
    def create_toolbar(self):
        """Üst toolbar'ı oluşturur (logout butonu için)."""
        toolbar = QToolBar("Ana Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Kullanıcı bilgisi
        user_label = QLabel(f"  👤 {self.user_data.get('email', 'Koordinatör')}  ")
        user_label.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 5px;")
        toolbar.addWidget(user_label)
        
        # Bölüm bilgisi
        dept_label = QLabel(f"  🏫 {self.user_data.get('department_name', 'Bölüm')}  ")
        dept_label.setStyleSheet("color: #34495e; padding: 5px;")
        toolbar.addWidget(dept_label)
        
        toolbar.addSeparator()
        
        # Spacer ekle (sağa yaslamak için)
        from PyQt5.QtWidgets import QSizePolicy
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

    def init_classroom_ui(self):
        """Derslik Yönetimi sekmesinin arayüzünü oluşturur."""
        main_layout = QHBoxLayout()

        # --- Sol Taraf: Derslik Ekleme/Düzenleme Formu ---
        form_container = QWidget()
        form_layout = QFormLayout()
        form_container.setLayout(form_layout)

        form_title = QLabel("Derslik Ekle / Düzenle")
        font = QFont();
        font.setPointSize(14);
        font.setBold(True)
        form_title.setFont(font)

        self.code_input = QLineEdit()
        self.name_input = QLineEdit()
        self.capacity_spinbox = QSpinBox()
        self.capacity_spinbox.setRange(1, 500)
        self.rows_spinbox = QSpinBox()  # Boyuna sıra (satır)
        self.rows_spinbox.setRange(1, 50)
        self.cols_spinbox = QSpinBox()  # Enine sıra (sütun)
        self.cols_spinbox.setRange(1, 50)
        self.seating_type_combobox = QComboBox()
        self.seating_type_combobox.addItems(["2", "3"])

        # Butonlar
        buttons_layout = QHBoxLayout()
        self.add_update_button = QPushButton("Ekle")
        self.add_update_button.clicked.connect(self.handle_add_update_classroom)
        self.clear_button = QPushButton("Formu Temizle")
        self.clear_button.clicked.connect(self.clear_form)
        buttons_layout.addWidget(self.add_update_button)
        buttons_layout.addWidget(self.clear_button)

        # Form elemanlarını layout'a ekle
        form_layout.addRow(form_title)
        form_layout.addRow("Derslik Kodu:", self.code_input)
        form_layout.addRow("Derslik Adı:", self.name_input)
        form_layout.addRow("Kapasite:", self.capacity_spinbox)
        form_layout.addRow("Boyuna Sıra (Satır):", self.rows_spinbox)
        form_layout.addRow("Enine Sıra (Sütun):", self.cols_spinbox)
        form_layout.addRow("Sıra Yapısı (Kaçarlı):", self.seating_type_combobox)
        form_layout.addRow(buttons_layout)

        # --- Sağ Taraf: Mevcut Derslikler Tablosu ve Arama ---
        table_container = QWidget()
        table_layout = QVBoxLayout()
        table_container.setLayout(table_layout)

        table_title = QLabel("Bölüme Ait Derslikler")
        table_title.setFont(font)

        # Arama ve Silme alanı
        actions_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Aramak için Derslik ID'si girin...")
        self.search_button = QPushButton("Ara ve Görselleştir")
        self.search_button.clicked.connect(self.handle_search_classroom)
        self.delete_button = QPushButton("Seçili Dersliği Sil")
        self.delete_button.clicked.connect(self.handle_delete_classroom)
        actions_layout.addWidget(self.search_input)
        actions_layout.addWidget(self.search_button)
        actions_layout.addWidget(self.delete_button)

        self.classrooms_table = QTableWidget()
        self.classrooms_table.setColumnCount(7)
        self.classrooms_table.setHorizontalHeaderLabels(
            ["ID", "Kod", "Ad", "Kapasite", "Satır", "Sütun", "Sıra Yapısı"])
        self.classrooms_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.classrooms_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.classrooms_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.classrooms_table.cellClicked.connect(self.handle_table_row_selection)

        table_layout.addWidget(table_title)
        table_layout.addLayout(actions_layout)
        table_layout.addWidget(self.classrooms_table)

        main_layout.addWidget(form_container, 1)
        main_layout.addWidget(table_container, 2)
        self.classroom_tab.setLayout(main_layout)

        self.load_classrooms_into_table()

    def init_course_upload_ui(self):
        """Ders Listesi Yükleme sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Ders Listesi Excel Dosyası Yükle")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Dosya seçme alanı
        file_layout = QHBoxLayout()
        self.course_file_input = QLineEdit()
        self.course_file_input.setPlaceholderText("Excel dosyası seçin...")
        self.course_file_input.setReadOnly(True)
        self.course_browse_button = QPushButton("Dosya Seç")
        self.course_browse_button.clicked.connect(self.browse_course_file)
        file_layout.addWidget(self.course_file_input)
        file_layout.addWidget(self.course_browse_button)
        
        # Yükleme butonu
        self.course_upload_button = QPushButton("Dersleri Yükle")
        self.course_upload_button.clicked.connect(self.handle_course_upload)
        
        # İlerleme çubuğu
        self.course_progress = QProgressBar()
        self.course_progress.setVisible(False)
        
        # Sonuç alanı
        self.course_result_text = QTextEdit()
        self.course_result_text.setMaximumHeight(200)
        self.course_result_text.setReadOnly(True)
        
        layout.addWidget(title)
        layout.addLayout(file_layout)
        layout.addWidget(self.course_upload_button)
        layout.addWidget(self.course_progress)
        layout.addWidget(QLabel("İşlem Sonuçları:"))
        layout.addWidget(self.course_result_text)
        
        self.course_upload_tab.setLayout(layout)

    def init_student_upload_ui(self):
        """Öğrenci Listesi Yükleme sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Öğrenci Listesi Excel Dosyası Yükle")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Dosya seçme alanı
        file_layout = QHBoxLayout()
        self.student_file_input = QLineEdit()
        self.student_file_input.setPlaceholderText("Excel dosyası seçin...")
        self.student_file_input.setReadOnly(True)
        self.student_browse_button = QPushButton("Dosya Seç")
        self.student_browse_button.clicked.connect(self.browse_student_file)
        file_layout.addWidget(self.student_file_input)
        file_layout.addWidget(self.student_browse_button)
        
        # Yükleme butonu
        self.student_upload_button = QPushButton("Öğrencileri Yükle")
        self.student_upload_button.clicked.connect(self.handle_student_upload)
        
        # İlerleme çubuğu
        self.student_progress = QProgressBar()
        self.student_progress.setVisible(False)
        
        # Sonuç alanı
        self.student_result_text = QTextEdit()
        self.student_result_text.setMaximumHeight(200)
        self.student_result_text.setReadOnly(True)
        
        layout.addWidget(title)
        layout.addLayout(file_layout)
        layout.addWidget(self.student_upload_button)
        layout.addWidget(self.student_progress)
        layout.addWidget(QLabel("İşlem Sonuçları:"))
        layout.addWidget(self.student_result_text)
        
        self.student_upload_tab.setLayout(layout)

    def init_student_list_ui(self):
        """Öğrenci Listesi sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Öğrenci Arama ve Ders Listesi")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Arama alanı
        search_layout = QHBoxLayout()
        search_label = QLabel("Öğrenci No:")
        self.student_search_input = QLineEdit()
        self.student_search_input.setPlaceholderText("Öğrenci numarası girin...")
        self.student_search_button = QPushButton("Ara")
        self.student_search_button.clicked.connect(self.handle_student_search)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.student_search_input)
        search_layout.addWidget(self.student_search_button)
        
        # Öğrenci bilgileri alanı
        self.student_info_text = QTextEdit()
        self.student_info_text.setReadOnly(True)
        self.student_info_text.setMaximumHeight(100)
        
        # Öğrencinin aldığı dersler tablosu
        courses_label = QLabel("Öğrencinin Aldığı Dersler:")
        courses_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        self.student_courses_table = QTableWidget()
        self.student_courses_table.setColumnCount(5)
        self.student_courses_table.setHorizontalHeaderLabels([
            "Ders Kodu", "Ders Adı", "Tür", "Sınıf", "Öğretim Üyesi"
        ])
        self.student_courses_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.student_courses_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(title)
        layout.addLayout(search_layout)
        layout.addWidget(QLabel("Öğrenci Bilgileri:"))
        layout.addWidget(self.student_info_text)
        layout.addWidget(courses_label)
        layout.addWidget(self.student_courses_table)
        
        self.student_list_tab.setLayout(layout)

    def init_course_list_ui(self):
        """Ders Listesi sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Ders Listesi ve Kayıtlı Öğrenciler")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Dersler listesi
        courses_label = QLabel("Dersler:")
        courses_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        self.courses_list_table = QTableWidget()
        self.courses_list_table.setColumnCount(5)
        self.courses_list_table.setHorizontalHeaderLabels([
            "Ders Kodu", "Ders Adı", "Tür", "Sınıf", "Öğretim Üyesi"
        ])
        self.courses_list_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.courses_list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.courses_list_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.courses_list_table.cellClicked.connect(self.handle_course_selection)
        
        # Seçili derse kayıtlı öğrenciler
        students_label = QLabel("Seçili Derse Kayıtlı Öğrenciler:")
        students_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        self.course_students_table = QTableWidget()
        self.course_students_table.setColumnCount(3)
        self.course_students_table.setHorizontalHeaderLabels([
            "Öğrenci No", "Ad Soyad", "Sınıf"
        ])
        self.course_students_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.course_students_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(title)
        layout.addWidget(courses_label)
        layout.addWidget(self.courses_list_table)
        layout.addWidget(students_label)
        layout.addWidget(self.course_students_table)
        
        self.course_list_tab.setLayout(layout)
        
        # Dersleri yükle
        self.load_courses_list()

    def handle_student_search(self):
        """Öğrenci arama işlemini gerçekleştirir."""
        from database import get_student_by_no, get_student_courses
        
        student_no = self.student_search_input.text().strip()
        if not student_no:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir öğrenci numarası girin.")
            return
        
        # Öğrenci bilgilerini al
        student = get_student_by_no(student_no)
        if not student:
            QMessageBox.information(self, "Bulunamadı", 
                f"'{student_no}' numaralı öğrenci bulunamadı.")
            self.student_info_text.clear()
            self.student_courses_table.setRowCount(0)
            return
        
        # Öğrenci bilgilerini göster
        info_text = f"Öğrenci No: {student['student_no']}\n"
        info_text += f"Ad Soyad: {student['full_name']}\n"
        info_text += f"Sınıf: {student['class_level']}"
        self.student_info_text.setText(info_text)
        
        # Öğrencinin aldığı dersleri al ve göster
        courses = get_student_courses(student_no)
        self.student_courses_table.setRowCount(len(courses))
        
        for row_num, course in enumerate(courses):
            self.student_courses_table.setItem(row_num, 0, QTableWidgetItem(course['code']))
            self.student_courses_table.setItem(row_num, 1, QTableWidgetItem(course['name']))
            self.student_courses_table.setItem(row_num, 2, QTableWidgetItem(course['course_type']))
            self.student_courses_table.setItem(row_num, 3, QTableWidgetItem(str(course['class_level'])))
            self.student_courses_table.setItem(row_num, 4, QTableWidgetItem(course['instructor_name']))
        
        if not courses:
            QMessageBox.information(self, "Bilgi", "Bu öğrenci henüz herhangi bir derse kayıtlı değil.")

    def load_courses_list(self):
        """Bölüme ait tüm dersleri yükler."""
        from database import get_all_courses_by_department
        
        courses = get_all_courses_by_department(self.department_id)
        self.courses_list_table.setRowCount(len(courses))
        
        for row_num, course in enumerate(courses):
            self.courses_list_table.setItem(row_num, 0, QTableWidgetItem(course['code']))
            self.courses_list_table.setItem(row_num, 1, QTableWidgetItem(course['name']))
            self.courses_list_table.setItem(row_num, 2, QTableWidgetItem(course['course_type']))
            self.courses_list_table.setItem(row_num, 3, QTableWidgetItem(str(course['class_level'])))
            self.courses_list_table.setItem(row_num, 4, QTableWidgetItem(course['instructor_name']))
            
            # Course ID'yi saklı tut (hidden olarak)
            self.courses_list_table.item(row_num, 0).setData(Qt.UserRole, course['id'])

    def handle_course_selection(self, row, column):
        """Ders seçildiğinde o derse kayıtlı öğrencileri gösterir."""
        from database import get_course_students
        
        # Seçili dersin ID'sini al
        course_id = self.courses_list_table.item(row, 0).data(Qt.UserRole)
        
        # Derse kayıtlı öğrencileri al
        students = get_course_students(course_id)
        self.course_students_table.setRowCount(len(students))
        
        for row_num, student in enumerate(students):
            self.course_students_table.setItem(row_num, 0, QTableWidgetItem(student['student_no']))
            self.course_students_table.setItem(row_num, 1, QTableWidgetItem(student['full_name']))
            self.course_students_table.setItem(row_num, 2, QTableWidgetItem(str(student['class_level'])))
        
        if not students:
            QMessageBox.information(self, "Bilgi", "Bu derse henüz kayıtlı öğrenci bulunmamaktadır.")

    def init_exam_schedule_ui(self):
        """Sınav Zamanlama sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Sınav Programı Oluştur - Kısıtlar")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Tarih seçimi
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Başlangıç Tarihi:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        date_layout.addWidget(self.start_date)
        
        date_layout.addWidget(QLabel("Bitiş Tarihi:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate().addDays(14))
        self.end_date.setCalendarPopup(True)
        date_layout.addWidget(self.end_date)
        
        # Hariç tutulacak günler
        excluded_days_layout = QHBoxLayout()
        excluded_days_layout.addWidget(QLabel("Hariç Tutulacak Günler:"))
        self.monday_excluded = QCheckBox("Pazartesi")
        self.tuesday_excluded = QCheckBox("Salı")
        self.wednesday_excluded = QCheckBox("Çarşamba")
        self.thursday_excluded = QCheckBox("Perşembe")
        self.friday_excluded = QCheckBox("Cuma")
        self.saturday_excluded = QCheckBox("Cumartesi")
        self.saturday_excluded.setChecked(True)
        self.sunday_excluded = QCheckBox("Pazar")
        self.sunday_excluded.setChecked(True)
        excluded_days_layout.addWidget(self.monday_excluded)
        excluded_days_layout.addWidget(self.tuesday_excluded)
        excluded_days_layout.addWidget(self.wednesday_excluded)
        excluded_days_layout.addWidget(self.thursday_excluded)
        excluded_days_layout.addWidget(self.friday_excluded)
        excluded_days_layout.addWidget(self.saturday_excluded)
        excluded_days_layout.addWidget(self.sunday_excluded)
        
        # Sınav türleri
        exam_types_layout = QHBoxLayout()
        exam_types_layout.addWidget(QLabel("Sınav Türleri:"))
        self.vize_checkbox = QCheckBox("Vize")
        self.vize_checkbox.setChecked(True)
        self.final_checkbox = QCheckBox("Final")
        self.final_checkbox.setChecked(True)
        self.butunleme_checkbox = QCheckBox("Bütünleme")
        exam_types_layout.addWidget(self.vize_checkbox)
        exam_types_layout.addWidget(self.final_checkbox)
        exam_types_layout.addWidget(self.butunleme_checkbox)
        
        # Varsayılan sınav süresi ve bekleme süresi
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Varsayılan Sınav Süresi (dk):"))
        self.default_exam_duration = QSpinBox()
        self.default_exam_duration.setRange(30, 240)
        self.default_exam_duration.setValue(120)
        self.default_exam_duration.setSingleStep(15)
        duration_layout.addWidget(self.default_exam_duration)
        
        duration_layout.addWidget(QLabel("Bekleme Süresi (dk):"))
        self.waiting_time = QSpinBox()
        self.waiting_time.setRange(0, 120)
        self.waiting_time.setValue(15)
        self.waiting_time.setSingleStep(15)
        duration_layout.addWidget(self.waiting_time)
        
        # Özel kısıtlar
        constraints_layout = QHBoxLayout()
        self.no_overlap_checkbox = QCheckBox("Hiçbir sınavın aynı anda olmaması")
        self.no_overlap_checkbox.setToolTip("Bu seçenek işaretlenirse, hiçbir dersin sınavı aynı zamanda başlamaz")
        constraints_layout.addWidget(self.no_overlap_checkbox)
        
        # Dersler listesi ve hariç tutma
        courses_group_layout = QVBoxLayout()
        courses_group_label = QLabel("Programa Dahil Edilecek Dersler:")
        courses_group_label.setFont(QFont("Arial", 11, QFont.Bold))
        courses_group_layout.addWidget(courses_group_label)
        
        # Dersler için arama ve seçim
        course_search_layout = QHBoxLayout()
        course_search_layout.addWidget(QLabel("Ara:"))
        self.course_search_filter = QLineEdit()
        self.course_search_filter.setPlaceholderText("Ders kodu veya adı ile ara...")
        self.course_search_filter.textChanged.connect(self.filter_courses_for_scheduling)
        course_search_layout.addWidget(self.course_search_filter)
        
        select_all_btn = QPushButton("Tümünü Seç")
        select_all_btn.clicked.connect(self.select_all_courses)
        course_search_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Tümünü Kaldır")
        deselect_all_btn.clicked.connect(self.deselect_all_courses)
        course_search_layout.addWidget(deselect_all_btn)
        
        courses_group_layout.addLayout(course_search_layout)
        
        # Dersler tablosu (checkbox'lı)
        self.scheduling_courses_table = QTableWidget()
        self.scheduling_courses_table.setColumnCount(6)
        self.scheduling_courses_table.setHorizontalHeaderLabels([
            "Seç", "Ders Kodu", "Ders Adı", "Tür", "Sınıf", "Özel Süre (dk)"
        ])
        self.scheduling_courses_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scheduling_courses_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.scheduling_courses_table.setMaximumHeight(200)
        courses_group_layout.addWidget(self.scheduling_courses_table)
        
        self.load_courses_for_scheduling()
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.generate_schedule_button = QPushButton("Sınav Programı Oluştur")
        self.generate_schedule_button.clicked.connect(self.handle_generate_schedule)
        self.sanitize_courses_button = QPushButton("Dersleri Temizle/Güncelle")
        self.sanitize_courses_button.clicked.connect(self.handle_sanitize_courses)
        self.clear_schedule_button = QPushButton("Mevcut Programı Temizle")
        self.clear_schedule_button.clicked.connect(self.handle_clear_schedule)
        button_layout.addWidget(self.generate_schedule_button)
        button_layout.addWidget(self.sanitize_courses_button)
        button_layout.addWidget(self.clear_schedule_button)
        
        info_label = QLabel("💡 İpucu: Kısıtları ayarlayıp 'Sınav Programı Oluştur' butonuna tıklayın")
        info_label.setStyleSheet("color: #0066cc; font-style: italic;")
        
        # İlerleme çubuğu
        self.schedule_progress = QProgressBar()
        self.schedule_progress.setVisible(False)
        
        # Sınav programı tablosu
        self.exams_table = QTableWidget()
        self.exams_table.setColumnCount(7)
        self.exams_table.setHorizontalHeaderLabels([
            "Sınav Türü", "Ders Kodu", "Ders Adı", "Sınıf", "Tarih", "Saat", "Öğretim Üyesi"
        ])
        self.exams_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.exams_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(title)
        layout.addLayout(date_layout)
        layout.addLayout(excluded_days_layout)
        layout.addLayout(exam_types_layout)
        layout.addLayout(duration_layout)
        layout.addLayout(constraints_layout)
        layout.addLayout(courses_group_layout)
        layout.addWidget(info_label)
        layout.addLayout(button_layout)
        layout.addWidget(self.schedule_progress)
        layout.addWidget(QLabel("Sınav Programı:"))
        layout.addWidget(self.exams_table)
        
        self.exam_schedule_tab.setLayout(layout)
        
        # Başlangıçta sınavları yükle
        self.load_scheduled_exams()

    def load_courses_for_scheduling(self):
        """Ders seçimi için dersleri yükler."""
        from database import get_all_courses_by_department
        
        courses = get_all_courses_by_department(self.department_id)
        self.scheduling_courses_table.setRowCount(len(courses))
        
        for row_num, course in enumerate(courses):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Varsayılan olarak tüm dersler seçili
            self.scheduling_courses_table.setCellWidget(row_num, 0, checkbox)
            
            # Ders bilgileri
            self.scheduling_courses_table.setItem(row_num, 1, QTableWidgetItem(course['code']))
            self.scheduling_courses_table.setItem(row_num, 2, QTableWidgetItem(course['name']))
            self.scheduling_courses_table.setItem(row_num, 3, QTableWidgetItem(course['course_type']))
            self.scheduling_courses_table.setItem(row_num, 4, QTableWidgetItem(str(course['class_level'])))
            
            # Özel süre için spinbox
            duration_spinbox = QSpinBox()
            duration_spinbox.setRange(30, 240)
            duration_spinbox.setValue(120)  # Varsayılan
            duration_spinbox.setSingleStep(15)
            duration_spinbox.setToolTip("Bu ders için özel sınav süresi (dakika)")
            self.scheduling_courses_table.setCellWidget(row_num, 5, duration_spinbox)
            
            # Course ID'yi saklı tut
            self.scheduling_courses_table.item(row_num, 1).setData(Qt.UserRole, course['id'])

    def filter_courses_for_scheduling(self, text):
        """Ders listesini filtreler."""
        for row in range(self.scheduling_courses_table.rowCount()):
            code_item = self.scheduling_courses_table.item(row, 1)
            name_item = self.scheduling_courses_table.item(row, 2)
            
            if code_item and name_item:
                code = code_item.text()
                name = name_item.text()
                
                # Arama metnini içeriyorsa göster
                if text.lower() in code.lower() or text.lower() in name.lower():
                    self.scheduling_courses_table.setRowHidden(row, False)
                else:
                    self.scheduling_courses_table.setRowHidden(row, True)

    def select_all_courses(self):
        """Tüm dersleri seçer."""
        for row in range(self.scheduling_courses_table.rowCount()):
            if not self.scheduling_courses_table.isRowHidden(row):
                checkbox = self.scheduling_courses_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)

    def deselect_all_courses(self):
        """Tüm derslerin seçimini kaldırır."""
        for row in range(self.scheduling_courses_table.rowCount()):
            if not self.scheduling_courses_table.isRowHidden(row):
                checkbox = self.scheduling_courses_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(False)

    def _format_time(self, value):
        """MySQL TIME alanı timedelta olarak dönebilir; HH:MM formatla."""
        try:
            from datetime import timedelta, datetime
            if hasattr(value, 'strftime'):
                return value.strftime('%H:%M')
            # mysql-connector TIME -> timedelta
            if isinstance(value, timedelta):
                total_seconds = int(value.total_seconds())
                hours = (total_seconds // 3600) % 24
                minutes = (total_seconds % 3600) // 60
                return f"{hours:02d}:{minutes:02d}"
            return str(value)
        except Exception:
            return str(value)

    def handle_generate_schedule(self):
        """Sınav programı oluşturma işlemini gerçekleştirir."""
        # Seçili sınav türlerini al
        exam_types = []
        if self.vize_checkbox.isChecked():
            exam_types.append('Vize')
        if self.final_checkbox.isChecked():
            exam_types.append('Final')
        if self.butunleme_checkbox.isChecked():
            exam_types.append('Bütünleme')
        
        if not exam_types:
            QMessageBox.warning(self, "Sınav Türü Seçilmedi", "Lütfen en az bir sınav türü seçin.")
            return
        
        # Tarih kontrolü
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        
        if start_date >= end_date:
            QMessageBox.warning(self, "Geçersiz Tarih", "Başlangıç tarihi bitiş tarihinden önce olmalıdır.")
            return
        
        # Seçili dersleri topla
        selected_courses = []
        course_durations = {}
        for row in range(self.scheduling_courses_table.rowCount()):
            checkbox = self.scheduling_courses_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                course_code_item = self.scheduling_courses_table.item(row, 1)
                if course_code_item:
                    course_id = course_code_item.data(Qt.UserRole)
                    selected_courses.append(course_id)
                    
                    # Özel süresi varsa al
                    duration_spinbox = self.scheduling_courses_table.cellWidget(row, 5)
                    if duration_spinbox:
                        course_durations[course_id] = duration_spinbox.value()
        
        if not selected_courses:
            QMessageBox.warning(self, "Ders Seçilmedi", "Lütfen en az bir ders seçin.")
            return
        
        # Hariç tutulacak günleri al
        excluded_days = []
        if self.monday_excluded.isChecked():
            excluded_days.append(0)  # Pazartesi
        if self.tuesday_excluded.isChecked():
            excluded_days.append(1)
        if self.wednesday_excluded.isChecked():
            excluded_days.append(2)
        if self.thursday_excluded.isChecked():
            excluded_days.append(3)
        if self.friday_excluded.isChecked():
            excluded_days.append(4)
        if self.saturday_excluded.isChecked():
            excluded_days.append(5)
        if self.sunday_excluded.isChecked():
            excluded_days.append(6)
        
        # Kısıtları topla
        constraints = {
            'default_duration': self.default_exam_duration.value(),
            'waiting_time': self.waiting_time.value(),
            'no_overlap': self.no_overlap_checkbox.isChecked(),
            'excluded_days': excluded_days,
            'selected_courses': selected_courses,
            'course_durations': course_durations
        }
        
        self.schedule_progress.setVisible(True)
        self.schedule_progress.setRange(0, 0)
        self.generate_schedule_button.setEnabled(False)
        
        try:
            scheduler = ExamScheduler(self.department_id)
            result = scheduler.generate_exam_schedule(start_date, end_date, exam_types, constraints)
            
            if result['success']:
                message = result['message']
                if result.get('warnings'):
                    message += "\n\n⚠️ Uyarılar:\n" + "\n".join(result['warnings'][:5])
                QMessageBox.information(self, "Başarılı", message)
                self.load_scheduled_exams()
            else:
                QMessageBox.critical(self, "Hata", result['message'])
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Sınav programı oluşturulurken hata: {str(e)}")
        finally:
            self.schedule_progress.setVisible(False)
            self.generate_schedule_button.setEnabled(True)

    def handle_sanitize_courses(self):
        ok, msg = sanitize_courses(self.department_id)
        if ok:
            QMessageBox.information(self, "Dersler Güncellendi", msg)
        else:
            QMessageBox.critical(self, "Hata", msg)

    def handle_clear_schedule(self):
        """Mevcut sınav programını temizler."""
        reply = QMessageBox.question(self, 'Temizleme Onayı',
                                   "Mevcut sınav programını silmek istediğinizden emin misiniz?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                scheduler = ExamScheduler(self.department_id)
                if scheduler.clear_existing_exams():
                    QMessageBox.information(self, "Başarılı", "Sınav programı temizlendi.")
                    self.load_scheduled_exams()
                else:
                    QMessageBox.critical(self, "Hata", "Sınav programı temizlenirken hata oluştu.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Temizleme işlemi sırasında hata: {str(e)}")

    def load_scheduled_exams(self):
        """Zamanlanmış sınavları tabloya yükler."""
        try:
            scheduler = ExamScheduler(self.department_id)
            exams = scheduler.get_scheduled_exams()
            
            self.exams_table.setRowCount(len(exams))
            
            for row_num, exam in enumerate(exams):
                self.exams_table.setItem(row_num, 0, QTableWidgetItem(exam['exam_type']))
                self.exams_table.setItem(row_num, 1, QTableWidgetItem(exam['course_code']))
                self.exams_table.setItem(row_num, 2, QTableWidgetItem(exam['course_name']))
                self.exams_table.setItem(row_num, 3, QTableWidgetItem(str(exam['class_level'])))
                self.exams_table.setItem(row_num, 4, QTableWidgetItem(exam['exam_date'].strftime('%d.%m.%Y')))
                self.exams_table.setItem(row_num, 5, QTableWidgetItem(self._format_time(exam['start_time'])))
                self.exams_table.setItem(row_num, 6, QTableWidgetItem(exam['instructor_name']))
                
        except Exception as e:
            print(f"Sınavlar yüklenirken hata: {e}")

    def init_seating_plan_ui(self):
        """Oturma Planı sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Oturma Planı Oluştur")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.generate_seating_button = QPushButton("Oturma Planları Oluştur")
        self.generate_seating_button.clicked.connect(self.handle_generate_seating)
        self.clear_seating_button = QPushButton("Oturma Planlarını Temizle")
        self.clear_seating_button.clicked.connect(self.handle_clear_seating)
        self.view_seating_button = QPushButton("Oturma Planını Görüntüle")
        self.view_seating_button.clicked.connect(self.handle_view_seating)
        button_layout.addWidget(self.generate_seating_button)
        button_layout.addWidget(self.clear_seating_button)
        button_layout.addWidget(self.view_seating_button)
        
        # İlerleme çubuğu
        self.seating_progress = QProgressBar()
        self.seating_progress.setVisible(False)
        
        # Sonuç alanı
        self.seating_result_text = QTextEdit()
        self.seating_result_text.setMaximumHeight(150)
        self.seating_result_text.setReadOnly(True)
        
        # Oturma planı tablosu
        self.seating_table = QTableWidget()
        self.seating_table.setColumnCount(6)
        self.seating_table.setHorizontalHeaderLabels([
            "Sınav", "Derslik", "Sıra", "Sütun", "Öğrenci No", "Ad Soyad"
        ])
        self.seating_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.seating_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(title)
        layout.addLayout(button_layout)
        layout.addWidget(self.seating_progress)
        layout.addWidget(QLabel("İşlem Sonuçları:"))
        layout.addWidget(self.seating_result_text)
        layout.addWidget(QLabel("Oturma Planları:"))
        layout.addWidget(self.seating_table)
        
        self.seating_plan_tab.setLayout(layout)

    def handle_generate_seating(self):
        """Oturma planları oluşturma işlemini gerçekleştirir."""
        self.seating_progress.setVisible(True)
        self.seating_progress.setRange(0, 0)
        self.generate_seating_button.setEnabled(False)
        
        try:
            planner = SeatingPlanner(self.department_id)
            results = planner.generate_seating_plans()
            
            # Sonuçları göster
            result_text = f"✅ Başarılı: {results['success']} oturma planı oluşturuldu\n"
            if results['warnings']:
                result_text += f"⚠️ Uyarılar:\n" + "\n".join(results['warnings'][:5]) + "\n"
            if results['errors']:
                result_text += f"❌ Hatalar:\n" + "\n".join(results['errors'][:5]) + "\n"
            
            self.seating_result_text.setText(result_text)
            
            if results['success'] > 0:
                QMessageBox.information(self, "Başarılı", f"{results['success']} oturma planı oluşturuldu.")
                self.load_seating_plans()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Oturma planı oluşturulurken hata: {str(e)}")
        finally:
            self.seating_progress.setVisible(False)
            self.generate_seating_button.setEnabled(True)

    def handle_clear_seating(self):
        """Oturma planlarını temizler."""
        reply = QMessageBox.question(self, 'Temizleme Onayı',
                                   "Tüm oturma planlarını silmek istediğinizden emin misiniz?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                planner = SeatingPlanner(self.department_id)
                if planner.clear_seating_plans():
                    QMessageBox.information(self, "Başarılı", "Oturma planları temizlendi.")
                    self.seating_table.setRowCount(0)
                    self.seating_result_text.clear()
                else:
                    QMessageBox.critical(self, "Hata", "Oturma planları temizlenirken hata oluştu.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Temizleme işlemi sırasında hata: {str(e)}")

    def handle_view_seating(self):
        """Oturma planını görselleştirir."""
        try:
            # Oturma planlarını tabloya yükle
            self.load_seating_plans()
            
            # Eğer tabloda veri varsa bilgi mesajı göster
            if self.seating_table.rowCount() > 0:
                QMessageBox.information(self, "Başarılı", 
                    f"Oturma planları tabloda gösteriliyor.\nToplam {self.seating_table.rowCount()} kayıt bulundu.")
            else:
                QMessageBox.warning(self, "Uyarı", 
                    "Henüz oluşturulmuş oturma planı bulunmamaktadır.\n"
                    "Lütfen önce 'Oturma Planları Oluştur' butonuna tıklayın.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Oturma planı yüklenirken hata: {str(e)}")

    def load_seating_plans(self):
        """Oturma planlarını tabloya yükler."""
        try:
            planner = SeatingPlanner(self.department_id)
            
            # Tüm sınavları al
            scheduler = ExamScheduler(self.department_id)
            exams = scheduler.get_scheduled_exams()
            
            all_seating_data = []
            for exam in exams:
                seating_data = planner.get_seating_plan(exam['id'])
                for seat in seating_data:
                    all_seating_data.append({
                        'exam': f"{exam['course_code']} - {exam['exam_type']}",
                        'classroom': seat['classroom_code'],
                        'row': seat['seat_row'],
                        'col': seat['seat_col'],
                        'student_no': seat['student_no'],
                        'student_name': seat['full_name']
                    })
            
            self.seating_table.setRowCount(len(all_seating_data))
            
            for row_num, data in enumerate(all_seating_data):
                self.seating_table.setItem(row_num, 0, QTableWidgetItem(data['exam']))
                self.seating_table.setItem(row_num, 1, QTableWidgetItem(data['classroom']))
                self.seating_table.setItem(row_num, 2, QTableWidgetItem(str(data['row'])))
                self.seating_table.setItem(row_num, 3, QTableWidgetItem(str(data['col'])))
                self.seating_table.setItem(row_num, 4, QTableWidgetItem(data['student_no']))
                self.seating_table.setItem(row_num, 5, QTableWidgetItem(data['student_name']))
                
        except Exception as e:
            print(f"Oturma planları yüklenirken hata: {e}")

    def init_schedule_view_ui(self):
        """Program Görünümü sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Sınav Programı Görselleştirme")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Görünüm seçenekleri
        view_options_layout = QHBoxLayout()
        view_options_layout.addWidget(QLabel("Görünüm Türü:"))
        self.view_type_combo = QComboBox()
        self.view_type_combo.addItems(["Tablo Görünümü", "Takvim Görünümü", "Derslik Bazlı Görünüm"])
        self.view_type_combo.currentTextChanged.connect(self.handle_view_type_change)
        view_options_layout.addWidget(self.view_type_combo)
        
        # Yenile butonu
        self.refresh_view_button = QPushButton("Yenile")
        self.refresh_view_button.clicked.connect(self.refresh_schedule_view)
        view_options_layout.addWidget(self.refresh_view_button)
        
        # Ana görünüm alanı
        self.schedule_view_widget = QWidget()
        self.schedule_view_layout = QVBoxLayout()
        self.schedule_view_widget.setLayout(self.schedule_view_layout)
        
        layout.addWidget(title)
        layout.addLayout(view_options_layout)
        layout.addWidget(self.schedule_view_widget)
        
        self.schedule_view_tab.setLayout(layout)
        
        # Başlangıçta tablo görünümünü yükle
        self.load_table_view()

    def handle_view_type_change(self, view_type):
        """Görünüm türü değiştiğinde ilgili görünümü yükler."""
        if view_type == "Tablo Görünümü":
            self.load_table_view()
        elif view_type == "Takvim Görünümü":
            self.load_calendar_view()
        elif view_type == "Derslik Bazlı Görünüm":
            self.load_classroom_view()

    def load_table_view(self):
        """Tablo görünümünü yükler."""
        # Mevcut widget'ları temizle
        self.clear_schedule_view()
        
        # Sınav programı tablosu
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(8)
        self.schedule_table.setHorizontalHeaderLabels([
            "Tarih", "Saat", "Sınav Türü", "Ders Kodu", "Ders Adı", 
            "Sınıf", "Öğretim Üyesi", "Derslikler"
        ])
        self.schedule_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.schedule_view_layout.addWidget(self.schedule_table)
        self.populate_schedule_table()

    def load_calendar_view(self):
        """Takvim görünümünü yükler."""
        # Mevcut widget'ları temizle
        self.clear_schedule_view()
        
        # Başlık ve kontroller için layout
        header_layout = QHBoxLayout()
        
        calendar_label = QLabel("Takvim Görünümü")
        calendar_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(calendar_label)
        
        # Hafta seçimi için butonlar
        self.prev_week_btn = QPushButton("◀ Önceki Hafta")
        self.prev_week_btn.clicked.connect(self.show_previous_week)
        self.next_week_btn = QPushButton("Sonraki Hafta ▶")
        self.next_week_btn.clicked.connect(self.show_next_week)
        self.current_week_btn = QPushButton("Bu Hafta")
        self.current_week_btn.clicked.connect(self.show_current_week)
        
        header_layout.addStretch()
        header_layout.addWidget(self.prev_week_btn)
        header_layout.addWidget(self.current_week_btn)
        header_layout.addWidget(self.next_week_btn)
        
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        self.schedule_view_layout.addWidget(header_widget)
        
        # Tarih aralığı gösterimi
        self.date_range_label = QLabel()
        self.date_range_label.setFont(QFont("Arial", 10))
        self.date_range_label.setStyleSheet("color: #555; margin: 5px;")
        self.schedule_view_layout.addWidget(self.date_range_label)
        
        # Takvim tablosu (7 gün x 4 saat)
        self.calendar_table = QTableWidget()
        self.calendar_table.setRowCount(4)  # 4 saat dilimi
        self.calendar_table.setColumnCount(7)  # 7 gün
        
        # Başlıkları ayarla
        time_slots = ["09:00-11:00", "11:00-13:00", "13:00-15:00", "15:00-17:00"]
        day_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        
        self.calendar_table.setVerticalHeaderLabels(time_slots)
        self.calendar_table.setHorizontalHeaderLabels(day_names)
        self.calendar_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.calendar_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.calendar_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.calendar_table.setMinimumHeight(400)
        
        # Stil ayarları
        self.calendar_table.setStyleSheet("""
            QTableWidget::item {
                padding: 10px;
                border: 1px solid #ddd;
            }
        """)
        
        self.schedule_view_layout.addWidget(self.calendar_table)
        
        # Başlangıç haftası (bugün)
        from datetime import datetime, timedelta
        today = datetime.now().date()
        self.current_week_start = today - timedelta(days=today.weekday())
        
        self.populate_calendar_table()

    def load_classroom_view(self):
        """Derslik bazlı görünümü yükler."""
        # Mevcut widget'ları temizle
        self.clear_schedule_view()
        
        # Başlık
        classroom_label = QLabel("Derslik Kullanım Tablosu")
        classroom_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.schedule_view_layout.addWidget(classroom_label)
        
        # Filtreleme için derslik seçici
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Derslik Filtrele:"))
        self.classroom_filter_combo = QComboBox()
        self.classroom_filter_combo.addItem("Tüm Derslikler", None)
        self.classroom_filter_combo.currentIndexChanged.connect(self.populate_classroom_table)
        filter_layout.addWidget(self.classroom_filter_combo)
        filter_layout.addStretch()
        
        filter_widget = QWidget()
        filter_widget.setLayout(filter_layout)
        self.schedule_view_layout.addWidget(filter_widget)
        
        # Derslikleri yükle
        self.load_classroom_filter_options()
        
        # Derslik bazlı tablo
        self.classroom_table = QTableWidget()
        self.classroom_table.setColumnCount(7)
        self.classroom_table.setHorizontalHeaderLabels([
            "Derslik", "Kapasite", "Tarih", "Saat", "Sınav Türü", "Ders", "Yerleştirilen Öğr."
        ])
        self.classroom_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.classroom_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.classroom_table.setSortingEnabled(True)
        
        self.schedule_view_layout.addWidget(self.classroom_table)
        self.populate_classroom_table()
    
    def load_classroom_filter_options(self):
        """Derslik filtre seçeneklerini yükler."""
        try:
            classrooms = get_classrooms_by_department(self.department_id)
            for classroom in classrooms:
                self.classroom_filter_combo.addItem(
                    f"{classroom['code']} - {classroom['name']}", 
                    classroom['id']
                )
        except Exception as e:
            print(f"Derslik filtreleri yüklenirken hata: {e}")

    def clear_schedule_view(self):
        """Görünüm alanını temizler."""
        while self.schedule_view_layout.count():
            child = self.schedule_view_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def populate_schedule_table(self):
        """Sınav programı tablosunu doldurur."""
        try:
            scheduler = ExamScheduler(self.department_id)
            exams = scheduler.get_scheduled_exams()
            
            self.schedule_table.setRowCount(len(exams))
            
            for row_num, exam in enumerate(exams):
                # Derslik bilgilerini al
                classroom_info = self.get_exam_classrooms(exam['id'])
                classroom_text = ", ".join([f"{c['code']}({c['capacity']})" for c in classroom_info])
                
                self.schedule_table.setItem(row_num, 0, QTableWidgetItem(exam['exam_date'].strftime('%d.%m.%Y')))
                self.schedule_table.setItem(row_num, 1, QTableWidgetItem(self._format_time(exam['start_time'])))
                self.schedule_table.setItem(row_num, 2, QTableWidgetItem(exam['exam_type']))
                self.schedule_table.setItem(row_num, 3, QTableWidgetItem(exam['course_code']))
                self.schedule_table.setItem(row_num, 4, QTableWidgetItem(exam['course_name']))
                self.schedule_table.setItem(row_num, 5, QTableWidgetItem(str(exam['class_level'])))
                self.schedule_table.setItem(row_num, 6, QTableWidgetItem(exam['instructor_name']))
                self.schedule_table.setItem(row_num, 7, QTableWidgetItem(classroom_text))
                
        except Exception as e:
            print(f"Sınav programı yüklenirken hata: {e}")

    def show_previous_week(self):
        """Önceki haftayı gösterir."""
        from datetime import timedelta
        self.current_week_start = self.current_week_start - timedelta(days=7)
        self.populate_calendar_table()
    
    def show_next_week(self):
        """Sonraki haftayı gösterir."""
        from datetime import timedelta
        self.current_week_start = self.current_week_start + timedelta(days=7)
        self.populate_calendar_table()
    
    def show_current_week(self):
        """Bu haftayı gösterir."""
        from datetime import datetime, timedelta
        today = datetime.now().date()
        self.current_week_start = today - timedelta(days=today.weekday())
        self.populate_calendar_table()
    
    def populate_calendar_table(self):
        """Takvim tablosunu doldurur."""
        try:
            scheduler = ExamScheduler(self.department_id)
            exams = scheduler.get_scheduled_exams()
            
            from datetime import timedelta
            
            # Haftanın günlerini oluştur
            week_days = [self.current_week_start + timedelta(days=i) for i in range(7)]
            
            # Tarih aralığını göster
            week_start_str = self.current_week_start.strftime('%d.%m.%Y')
            week_end_str = (self.current_week_start + timedelta(days=6)).strftime('%d.%m.%Y')
            self.date_range_label.setText(f"📅 {week_start_str} - {week_end_str}")
            
            # Sınavları günlere göre grupla
            daily_exams = {}
            for exam in exams:
                exam_date = exam['exam_date']
                if exam_date in week_days:
                    day_index = week_days.index(exam_date)
                    if day_index not in daily_exams:
                        daily_exams[day_index] = []
                    daily_exams[day_index].append(exam)
            
            # Saat dilimlerine göre yerleştir
            time_slots = [
                (9, 0), (11, 0), (13, 0), (15, 0)
            ]
            
            # Tüm hücreleri temizle
            self.calendar_table.clearContents()
            
            for time_index, (hour, minute) in enumerate(time_slots):
                for day_index in range(7):
                    cell_text = ""
                    cell_color = QColor(255, 255, 255)  # Beyaz (boş)
                    
                    if day_index in daily_exams:
                        for exam in daily_exams[day_index]:
                            # start_time timedelta olabilir, saati al
                            exam_hour = self._get_hour_from_time(exam['start_time'])
                            if exam_hour == hour:
                                cell_text += f"📚 {exam['course_code']}\n"
                                cell_text += f"📝 {exam['exam_type']}\n"
                                cell_text += f"👤 {exam['instructor_name']}\n"
                                cell_color = QColor(220, 240, 255)  # Açık mavi
                    
                    item = QTableWidgetItem(cell_text.strip() if cell_text else "")
                    item.setBackground(cell_color)
                    
                    # Bugünü vurgula
                    from datetime import datetime
                    if week_days[day_index] == datetime.now().date():
                        item.setBackground(QColor(255, 255, 220))  # Sarı tonu
                    
                    self.calendar_table.setItem(time_index, day_index, item)
                
        except Exception as e:
            print(f"Takvim görünümü yüklenirken hata: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_hour_from_time(self, time_value):
        """TIME alanından saat değerini çıkarır (timedelta veya time objesi olabilir)."""
        try:
            from datetime import timedelta
            if isinstance(time_value, timedelta):
                total_seconds = int(time_value.total_seconds())
                hours = (total_seconds // 3600) % 24
                return hours
            elif hasattr(time_value, 'hour'):
                return time_value.hour
            return 0
        except Exception:
            return 0

    def populate_classroom_table(self):
        """Derslik bazlı tabloyu doldurur."""
        try:
            # Seçili derslik filtresini al
            selected_classroom_id = None
            if hasattr(self, 'classroom_filter_combo'):
                selected_classroom_id = self.classroom_filter_combo.currentData()
            
            # Derslik atamalarını al
            classroom_assignments = self.get_classroom_assignments(selected_classroom_id)
            
            self.classroom_table.setRowCount(len(classroom_assignments))
            
            for row_num, assignment in enumerate(classroom_assignments):
                # Derslik kodu
                classroom_item = QTableWidgetItem(assignment['classroom_code'])
                self.classroom_table.setItem(row_num, 0, classroom_item)
                
                # Kapasite
                capacity_item = QTableWidgetItem(str(assignment['capacity']))
                self.classroom_table.setItem(row_num, 1, capacity_item)
                
                # Tarih
                date_item = QTableWidgetItem(assignment['exam_date'].strftime('%d.%m.%Y'))
                self.classroom_table.setItem(row_num, 2, date_item)
                
                # Saat
                time_item = QTableWidgetItem(self._format_time(assignment['start_time']))
                self.classroom_table.setItem(row_num, 3, time_item)
                
                # Sınav türü
                type_item = QTableWidgetItem(assignment['exam_type'])
                self.classroom_table.setItem(row_num, 4, type_item)
                
                # Ders
                course_item = QTableWidgetItem(f"{assignment['course_code']} - {assignment['course_name']}")
                self.classroom_table.setItem(row_num, 5, course_item)
                
                # Yerleştirilen öğrenci sayısı
                student_count = assignment['student_count']
                capacity = assignment['capacity']
                usage_percent = (student_count / capacity * 100) if capacity > 0 else 0
                
                student_item = QTableWidgetItem(f"{student_count} / {capacity} ({usage_percent:.0f}%)")
                
                # Doluluk oranına göre renklendirme
                if usage_percent > 90:
                    student_item.setBackground(QColor(255, 200, 200))  # Kırmızımsı (çok dolu)
                elif usage_percent > 70:
                    student_item.setBackground(QColor(255, 255, 200))  # Sarımsı (orta)
                else:
                    student_item.setBackground(QColor(200, 255, 200))  # Yeşilimsi (uygun)
                
                self.classroom_table.setItem(row_num, 6, student_item)
                
        except Exception as e:
            print(f"Derslik görünümü yüklenirken hata: {e}")
            import traceback
            traceback.print_exc()

    def get_exam_classrooms(self, exam_id):
        """Belirli bir sınavın derslik bilgilerini getirir."""
        connection = get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT cl.code, cl.name, cl.capacity
                FROM exam_assignments ea
                JOIN classrooms cl ON ea.classroom_id = cl.id
                WHERE ea.exam_id = %s
            """
            cursor.execute(query, (exam_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Derslik bilgileri alınırken hata: {e}")
            return []
        finally:
            connection.close()

    def get_classroom_assignments(self, classroom_id=None):
        """Derslik atamalarını getirir."""
        connection = get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            if classroom_id:
                # Belirli bir derslik için
                query = """
                    SELECT e.exam_date, e.start_time, c.code as course_code, c.name as course_name,
                           e.exam_type, cl.code as classroom_code, cl.capacity,
                           COUNT(sa.student_id) as student_count
                    FROM exams e
                    JOIN courses c ON e.course_id = c.id
                    JOIN exam_assignments ea ON e.id = ea.exam_id
                    JOIN classrooms cl ON ea.classroom_id = cl.id
                    LEFT JOIN seating_assignments sa ON e.id = sa.exam_id AND cl.id = sa.classroom_id
                    WHERE c.department_id = %s AND cl.id = %s
                    GROUP BY e.id, cl.id
                    ORDER BY e.exam_date, e.start_time
                """
                cursor.execute(query, (self.department_id, classroom_id))
            else:
                # Tüm derslikler
                query = """
                    SELECT e.exam_date, e.start_time, c.code as course_code, c.name as course_name,
                           e.exam_type, cl.code as classroom_code, cl.capacity,
                           COUNT(sa.student_id) as student_count
                    FROM exams e
                    JOIN courses c ON e.course_id = c.id
                    JOIN exam_assignments ea ON e.id = ea.exam_id
                    JOIN classrooms cl ON ea.classroom_id = cl.id
                    LEFT JOIN seating_assignments sa ON e.id = sa.exam_id AND cl.id = sa.classroom_id
                    WHERE c.department_id = %s
                    GROUP BY e.id, cl.id
                    ORDER BY cl.code, e.exam_date, e.start_time
                """
                cursor.execute(query, (self.department_id,))
            
            return cursor.fetchall()
        except Exception as e:
            print(f"Derslik atamaları alınırken hata: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            connection.close()

    def refresh_schedule_view(self):
        """Görünümü yeniler."""
        current_view = self.view_type_combo.currentText()
        if current_view == "Tablo Görünümü":
            self.load_table_view()
        elif current_view == "Takvim Görünümü":
            self.load_calendar_view()
        elif current_view == "Derslik Bazlı Görünüm":
            self.load_classroom_view()

    def init_export_ui(self):
        """Dışa Aktarma sekmesinin arayüzünü oluşturur."""
        layout = QVBoxLayout()
        
        title = QLabel("Rapor ve Dışa Aktarma")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Excel dışa aktarma
        excel_group = QWidget()
        excel_layout = QVBoxLayout()
        excel_group.setLayout(excel_layout)
        
        excel_title = QLabel("Excel Dışa Aktarma")
        excel_title.setFont(QFont("Arial", 12, QFont.Bold))
        excel_layout.addWidget(excel_title)
        
        excel_buttons_layout = QHBoxLayout()
        self.export_schedule_excel_button = QPushButton("Sınav Programını Excel'e Aktar")
        self.export_schedule_excel_button.clicked.connect(self.handle_export_schedule_excel)
        self.export_seating_excel_button = QPushButton("Oturma Planlarını Excel'e Aktar")
        self.export_seating_excel_button.clicked.connect(self.handle_export_seating_excel)
        self.export_comprehensive_excel_button = QPushButton("Kapsamlı Raporu Excel'e Aktar")
        self.export_comprehensive_excel_button.clicked.connect(self.handle_export_comprehensive_excel)
        
        excel_buttons_layout.addWidget(self.export_schedule_excel_button)
        excel_buttons_layout.addWidget(self.export_seating_excel_button)
        excel_buttons_layout.addWidget(self.export_comprehensive_excel_button)
        excel_layout.addLayout(excel_buttons_layout)
        
        # PDF dışa aktarma
        pdf_group = QWidget()
        pdf_layout = QVBoxLayout()
        pdf_group.setLayout(pdf_layout)
        
        pdf_title = QLabel("PDF Dışa Aktarma")
        pdf_title.setFont(QFont("Arial", 12, QFont.Bold))
        pdf_layout.addWidget(pdf_title)
        
        pdf_buttons_layout = QHBoxLayout()
        self.export_pdf_button = QPushButton("Sınav Programını PDF'e Aktar")
        self.export_pdf_button.clicked.connect(self.handle_export_pdf)
        pdf_buttons_layout.addWidget(self.export_pdf_button)
        pdf_layout.addLayout(pdf_buttons_layout)
        
        # İlerleme çubuğu
        self.export_progress = QProgressBar()
        self.export_progress.setVisible(False)
        
        # Sonuç alanı
        self.export_result_text = QTextEdit()
        self.export_result_text.setMaximumHeight(150)
        self.export_result_text.setReadOnly(True)
        
        layout.addWidget(title)
        layout.addWidget(excel_group)
        layout.addWidget(pdf_group)
        layout.addWidget(self.export_progress)
        layout.addWidget(QLabel("İşlem Sonuçları:"))
        layout.addWidget(self.export_result_text)
        
        self.export_tab.setLayout(layout)

    def handle_export_schedule_excel(self):
        """Sınav programını Excel'e aktarır."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Sınav Programını Kaydet", "sinav_programi.xlsx", "Excel Dosyaları (*.xlsx)")
        
        if file_path:
            self.export_progress.setVisible(True)
            self.export_progress.setRange(0, 0)
            
            try:
                export_manager = ExportManager(self.department_id)
                success, message = export_manager.export_schedule_to_excel(file_path)
                
                self.export_result_text.setText(message)
                
                if success:
                    QMessageBox.information(self, "Başarılı", message)
                else:
                    QMessageBox.critical(self, "Hata", message)
                    
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dışa aktarma sırasında hata: {str(e)}")
            finally:
                self.export_progress.setVisible(False)

    def handle_export_seating_excel(self):
        """Oturma planlarını Excel'e aktarır."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Oturma Planlarını Kaydet", "oturma_planlari.xlsx", "Excel Dosyaları (*.xlsx)")
        
        if file_path:
            self.export_progress.setVisible(True)
            self.export_progress.setRange(0, 0)
            
            try:
                export_manager = ExportManager(self.department_id)
                success, message = export_manager.export_seating_plans_to_excel(file_path)
                
                self.export_result_text.setText(message)
                
                if success:
                    QMessageBox.information(self, "Başarılı", message)
                else:
                    QMessageBox.critical(self, "Hata", message)
                    
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dışa aktarma sırasında hata: {str(e)}")
            finally:
                self.export_progress.setVisible(False)

    def handle_export_comprehensive_excel(self):
        """Kapsamlı raporu Excel'e aktarır."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Kapsamlı Raporu Kaydet", "kapsamli_rapor.xlsx", "Excel Dosyaları (*.xlsx)")
        
        if file_path:
            self.export_progress.setVisible(True)
            self.export_progress.setRange(0, 0)
            
            try:
                export_manager = ExportManager(self.department_id)
                success, message = export_manager.export_comprehensive_report_to_excel(file_path)
                
                self.export_result_text.setText(message)
                
                if success:
                    QMessageBox.information(self, "Başarılı", message)
                else:
                    QMessageBox.critical(self, "Hata", message)
                    
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dışa aktarma sırasında hata: {str(e)}")
            finally:
                self.export_progress.setVisible(False)

    def handle_export_pdf(self):
        """Sınav programını PDF'e aktarır."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Sınav Programını PDF'e Kaydet", "sinav_programi.pdf", "PDF Dosyaları (*.pdf)")
        
        if file_path:
            self.export_progress.setVisible(True)
            self.export_progress.setRange(0, 0)
            
            try:
                export_manager = ExportManager(self.department_id)
                success, message = export_manager.generate_pdf_report(file_path)
                
                self.export_result_text.setText(message)
                
                if success:
                    QMessageBox.information(self, "Başarılı", message)
                else:
                    QMessageBox.critical(self, "Hata", message)
                    
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dışa aktarma sırasında hata: {str(e)}")
            finally:
                self.export_progress.setVisible(False)

    def browse_course_file(self):
        """Ders listesi dosyası seçme dialogunu açar."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Ders Listesi Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)")
        if file_path:
            self.course_file_input.setText(file_path)

    def browse_student_file(self):
        """Öğrenci listesi dosyası seçme dialogunu açar."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Öğrenci Listesi Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)")
        if file_path:
            self.student_file_input.setText(file_path)

    def handle_course_upload(self):
        """Ders listesi yükleme işlemini gerçekleştirir."""
        file_path = self.course_file_input.text().strip()
        if not file_path:
            QMessageBox.warning(self, "Dosya Seçilmedi", "Lütfen bir Excel dosyası seçin.")
            return
        
        self.course_progress.setVisible(True)
        self.course_progress.setRange(0, 0)  # Belirsiz ilerleme
        self.course_upload_button.setEnabled(False)
        
        # QThread ile arka planda çalıştır
        self.course_thread = QThread()
        self.course_worker = ExcelWorker('courses', file_path, self.department_id)
        self.course_worker.moveToThread(self.course_thread)
        self.course_thread.started.connect(self.course_worker.run)
        self.course_worker.finished.connect(self.on_course_finished)
        self.course_worker.error.connect(self.on_course_error)
        # Temizlik
        self.course_worker.finished.connect(self.course_thread.quit)
        self.course_worker.finished.connect(self.course_worker.deleteLater)
        self.course_thread.finished.connect(self.course_thread.deleteLater)
        self.course_thread.start()

    def on_course_finished(self, results):
        # Sonuçları göster
        result_text = f"✅ Başarılı: {results['success']} ders eklendi\n"
        if results.get('warnings'):
            result_text += f"⚠️ Uyarılar:\n" + "\n".join(results['warnings'][:10]) + "\n"
        if results.get('errors'):
            result_text += f"❌ Hatalar:\n" + "\n".join(results['errors'][:10]) + "\n"
        self.course_result_text.setText(result_text)
        if results.get('success', 0) > 0:
            QMessageBox.information(self, "Başarılı", f"{results['success']} ders başarıyla yüklendi.")
        self.course_progress.setVisible(False)
        self.course_upload_button.setEnabled(True)

    def on_course_error(self, message):
        QMessageBox.critical(self, "Hata", f"Dosya işlenirken hata oluştu: {message}")
        self.course_progress.setVisible(False)
        self.course_upload_button.setEnabled(True)

    def handle_student_upload(self):
        """Öğrenci listesi yükleme işlemini gerçekleştirir."""
        file_path = self.student_file_input.text().strip()
        if not file_path:
            QMessageBox.warning(self, "Dosya Seçilmedi", "Lütfen bir Excel dosyası seçin.")
            return
        
        self.student_progress.setVisible(True)
        self.student_progress.setRange(0, 0)  # Belirsiz ilerleme
        self.student_upload_button.setEnabled(False)
        
        # QThread ile arka planda çalıştır
        self.student_thread = QThread()
        self.student_worker = ExcelWorker('students', file_path)
        self.student_worker.moveToThread(self.student_thread)
        self.student_thread.started.connect(self.student_worker.run)
        self.student_worker.finished.connect(self.on_student_finished)
        self.student_worker.error.connect(self.on_student_error)
        # Temizlik
        self.student_worker.finished.connect(self.student_thread.quit)
        self.student_worker.finished.connect(self.student_worker.deleteLater)
        self.student_thread.finished.connect(self.student_thread.deleteLater)
        self.student_thread.start()

    def on_student_finished(self, results):
        result_text = f"✅ Başarılı: {results['success']} öğrenci eklendi\n"
        result_text += f"📚 Kayıtlar: {results.get('enrollments', 0)} ders kaydı oluşturuldu\n"
        if results.get('warnings'):
            result_text += f"⚠️ Uyarılar:\n" + "\n".join(results['warnings'][:10]) + "\n"
        if results.get('errors'):
            result_text += f"❌ Hatalar:\n" + "\n".join(results['errors'][:10]) + "\n"
        self.student_result_text.setText(result_text)
        if results.get('success', 0) > 0:
            QMessageBox.information(self, "Başarılı", 
                f"{results['success']} öğrenci ve {results.get('enrollments', 0)} kayıt başarıyla yüklendi.")
        self.student_progress.setVisible(False)
        self.student_upload_button.setEnabled(True)

    def on_student_error(self, message):
        QMessageBox.critical(self, "Hata", f"Dosya işlenirken hata oluştu: {message}")
        self.student_progress.setVisible(False)
        self.student_upload_button.setEnabled(True)

    def load_classrooms_into_table(self):
        """Veritabanından derslikleri alıp tabloya yükler."""
        self.classrooms_table.setRowCount(0)
        classrooms = get_classrooms_by_department(self.department_id)
        if not classrooms:  # Eğer hiç derslik yoksa diğer tabları pasif yap
            self.tabs.setTabEnabled(1, False)
            self.tabs.setTabEnabled(2, False)
            self.tabs.setTabEnabled(3, False)
            self.tabs.setTabEnabled(4, False)
            self.tabs.setTabEnabled(5, False)
            self.tabs.setTabEnabled(6, False)
            self.tabs.setTabEnabled(7, False)
            self.tabs.setTabEnabled(8, False)
        else:  # Derslik varsa aktif yap
            self.tabs.setTabEnabled(1, True)
            self.tabs.setTabEnabled(2, True)
            self.tabs.setTabEnabled(3, True)
            self.tabs.setTabEnabled(4, True)
            self.tabs.setTabEnabled(5, True)
            self.tabs.setTabEnabled(6, True)
            self.tabs.setTabEnabled(7, True)
            self.tabs.setTabEnabled(8, True)

        for row_num, classroom in enumerate(classrooms):
            self.classrooms_table.insertRow(row_num)
            self.classrooms_table.setItem(row_num, 0, QTableWidgetItem(str(classroom['id'])))
            self.classrooms_table.setItem(row_num, 1, QTableWidgetItem(classroom['code']))
            self.classrooms_table.setItem(row_num, 2, QTableWidgetItem(classroom['name']))
            self.classrooms_table.setItem(row_num, 3, QTableWidgetItem(str(classroom['capacity'])))
            self.classrooms_table.setItem(row_num, 4, QTableWidgetItem(str(classroom['rows_count'])))
            self.classrooms_table.setItem(row_num, 5, QTableWidgetItem(str(classroom['cols_count'])))
            self.classrooms_table.setItem(row_num, 6, QTableWidgetItem(str(classroom['seating_type'])))

    def handle_table_row_selection(self, row, column):
        """Tablodan bir satır seçildiğinde formun doldurulmasını sağlar."""
        self.selected_classroom_id = int(self.classrooms_table.item(row, 0).text())

        self.code_input.setText(self.classrooms_table.item(row, 1).text())
        self.name_input.setText(self.classrooms_table.item(row, 2).text())
        self.capacity_spinbox.setValue(int(self.classrooms_table.item(row, 3).text()))
        self.rows_spinbox.setValue(int(self.classrooms_table.item(row, 4).text()))
        self.cols_spinbox.setValue(int(self.classrooms_table.item(row, 5).text()))
        self.seating_type_combobox.setCurrentText(self.classrooms_table.item(row, 6).text())

        self.add_update_button.setText("Güncelle")

    def clear_form(self):
        """Formu temizler ve ekleme moduna geri döner."""
        self.selected_classroom_id = None
        self.code_input.clear()
        self.name_input.clear()
        self.capacity_spinbox.setValue(1)
        self.rows_spinbox.setValue(1)
        self.cols_spinbox.setValue(1)
        self.seating_type_combobox.setCurrentIndex(0)
        self.add_update_button.setText("Ekle")
        self.classrooms_table.clearSelection()

    def handle_add_update_classroom(self):
        """Ekle veya Güncelle butonuna basıldığında çalışır."""
        classroom_data = {
            'department_id': self.department_id,
            'code': self.code_input.text().strip(),
            'name': self.name_input.text().strip(),
            'capacity': self.capacity_spinbox.value(),
            'rows_count': self.rows_spinbox.value(),
            'cols_count': self.cols_spinbox.value(),
            'seating_type': int(self.seating_type_combobox.currentText())
        }

        if not classroom_data['code'] or not classroom_data['name']:
            QMessageBox.warning(self, "Eksik Bilgi", "Derslik Kodu ve Adı boş bırakılamaz.")
            return

        if self.selected_classroom_id:  # Güncelleme modu
            success, message = update_classroom(self.selected_classroom_id, classroom_data)
        else:  # Ekleme modu
            success, message = add_classroom(classroom_data)

        if success:
            QMessageBox.information(self, "Başarılı", message)
            self.load_classrooms_into_table()
            self.clear_form()
        else:
            QMessageBox.critical(self, "Hata", message)

    def handle_delete_classroom(self):
        """Seçili dersliği silme işlemini gerçekleştirir."""
        if not self.selected_classroom_id:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen silmek için tablodan bir derslik seçin.")
            return

        reply = QMessageBox.question(self, 'Silme Onayı',
                                     f"ID: {self.selected_classroom_id} olan dersliği silmek istediğinizden emin misiniz?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            success, message = delete_classroom(self.selected_classroom_id)
            if success:
                QMessageBox.information(self, "Başarılı", message)
                self.load_classrooms_into_table()
                self.clear_form()
            else:
                QMessageBox.critical(self, "Hata", message)

    def handle_search_classroom(self):
        """ID ile derslik arar ve bulursa görselleştirir."""
        search_id_text = self.search_input.text().strip()
        if not search_id_text.isdigit():
            QMessageBox.warning(self, "Geçersiz ID", "Lütfen aramak için geçerli bir sayısal ID girin.")
            return

        classroom_id = int(search_id_text)
        classroom_details = get_classroom_details(classroom_id, self.department_id)

        if classroom_details:
            # Görselleştirme penceresini aç
            dialog = ClassroomVisualizer(classroom_details, self)
            dialog.exec_()
        else:
            QMessageBox.information(self, "Bulunamadı",
                                    f"ID: {classroom_id} olan bir derslik bulunamadı veya bu bölüme ait değil.")


class ClassroomVisualizer(QDialog):
    """Derslik oturma düzenini görselleştiren pencere."""

    def __init__(self, classroom_data, parent=None):
        super().__init__(parent)
        self.data = classroom_data
        self.setWindowTitle(f"Oturma Düzeni: {self.data['code']} - {self.data['name']}")
        
        main_layout = QVBoxLayout()
        
        # Başlık bilgileri
        info_layout = QHBoxLayout()
        info_label = QLabel(f"📋 Derslik: {self.data['code']} - {self.data['name']}")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_layout.addWidget(info_label)
        
        capacity_label = QLabel(f"👥 Kapasite: {self.data['capacity']}")
        capacity_label.setFont(QFont("Arial", 10))
        info_layout.addWidget(capacity_label)
        
        seating_info = QLabel(f"🪑 {self.data['seating_type']}'li Sıra Düzeni")
        seating_info.setFont(QFont("Arial", 10))
        info_layout.addWidget(seating_info)
        info_layout.addStretch()
        
        main_layout.addLayout(info_layout)
        
        # Ayraç çizgisi
        line = QLabel()
        line.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line)
        
        # Sahne/Tahta gösterimi
        stage_label = QLabel("🎓 TAHTA / SAHNE 🎓")
        stage_label.setAlignment(Qt.AlignCenter)
        stage_label.setStyleSheet("""
            background-color: #2c3e50; 
            color: white; 
            padding: 10px; 
            font-weight: bold; 
            border-radius: 5px;
            font-size: 14px;
        """)
        main_layout.addWidget(stage_label)
        main_layout.addSpacing(20)
        
        # Koltuk düzeni için grid layout
        grid_widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(3)
        
        rows = self.data['rows_count']
        cols = self.data['cols_count']
        seating_type = self.data['seating_type']
        
        # Sıralar ve boşluklar için kolon hesaplama
        # Her seating_type kadar koltuğun ardından bir boşluk kolonu ekleriz
        grid_col_position = 0
        
        for r in range(rows):
            grid_col_position = 0  # Her satırda baştan başla
            
            for c in range(cols):
                # Her sırayı bir grup olarak ele al
                group_index = c // seating_type
                position_in_group = c % seating_type
                
                # Grup rengini belirle
                if group_index % 2 == 0:
                    color = QColor("#87CEEB")  # Açık mavi
                else:
                    color = QColor("#98FB98")  # Açık yeşil
                
                seat = QLabel(f"💺\nS{r + 1}-K{c + 1}")
                seat.setAlignment(Qt.AlignCenter)
                seat.setMinimumSize(70, 55)
                seat.setMaximumSize(70, 55)
                seat.setAutoFillBackground(True)
                
                palette = seat.palette()
                palette.setColor(seat.backgroundRole(), color)
                seat.setPalette(palette)
                
                seat.setStyleSheet("""
                    border: 2px solid #2c3e50; 
                    border-radius: 8px;
                    font-size: 9px;
                    font-weight: bold;
                """)
                
                # Grid'e ekle
                layout.addWidget(seat, r, grid_col_position)
                grid_col_position += 1
                
                # Grup sonu mu? (seating_type'a göre)
                if (c + 1) % seating_type == 0 and c < cols - 1:
                    # Boşluk kolonu ekle (koridor)
                    spacer = QLabel()
                    spacer.setMinimumWidth(25)
                    spacer.setMaximumWidth(25)
                    spacer.setStyleSheet("background-color: #ecf0f1;")
                    layout.addWidget(spacer, r, grid_col_position)
                    grid_col_position += 1
        
        grid_widget.setLayout(layout)
        main_layout.addWidget(grid_widget, alignment=Qt.AlignCenter)
        
        # Alt bilgi
        main_layout.addSpacing(20)
        footer_label = QLabel(f"Toplam {rows} sıra × {cols} koltuk = {rows * cols} kişilik kapasite")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        main_layout.addWidget(footer_label)
        
        # Renk açıklamaları
        legend_layout = QHBoxLayout()
        legend_layout.addStretch()
        
        legend1 = QLabel("🟦 Grup 1, 3, 5...")
        legend1.setStyleSheet("color: #3498db;")
        legend_layout.addWidget(legend1)
        
        legend2 = QLabel("🟩 Grup 2, 4, 6...")
        legend2.setStyleSheet("color: #2ecc71;")
        legend_layout.addWidget(legend2)
        
        legend_layout.addStretch()
        main_layout.addLayout(legend_layout)
        
        self.setLayout(main_layout)
        self.setMinimumSize(800, 600)

    # def init_debug_ui(self):
    #     """Debug sekmesinin arayüzünü oluşturur."""
    #     pass  # Geçici olarak devre dışı

    # def browse_debug_file(self):
    #     """Debug dosyası seçme dialogunu açar."""
    #     pass  # Geçici olarak devre dışı

    # def handle_debug_excel(self):
    #     """Excel dosyasının yapısını analiz eder."""
    #     pass  # Geçici olarak devre dışı

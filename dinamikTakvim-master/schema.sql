CREATE DATABASE IF NOT EXISTS sinav_takvimi_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_turkish_ci;

USE sinav_takvimi_db;

-- -----------------------------------------------------
-- Tablo 1: `departments` (Bölümler)
-- Sistemde tanımlı olan 5 ana bölümü saklar.
-- Diğer birçok tablo bu tabloya referans verir.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
                                           id INT NOT NULL AUTO_INCREMENT,
                                           name VARCHAR(255) NOT NULL UNIQUE,
                                           PRIMARY KEY (id)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Tablo 2: `users` (Kullanıcılar)
-- Sisteme giriş yapacak 'admin' ve 'coordinator' rollerini tutar.
-- Koordinatörler bir bölüme bağlıyken, admin'in bölümü yoktur (NULL).
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
                                     id INT NOT NULL AUTO_INCREMENT,
                                     email VARCHAR(255) NOT NULL UNIQUE,
                                     password VARCHAR(255) NOT NULL, -- Not: Gerçek bir uygulamada şifreler her zaman hash'lenerek saklanmalıdır.
                                     role ENUM('admin', 'coordinator') NOT NULL,
                                     department_id INT NULL, -- Admin için bu alan NULL olacaktır.
                                     PRIMARY KEY (id),
                                     CONSTRAINT fk_users_departments
                                         FOREIGN KEY (department_id)
                                             REFERENCES departments(id)
                                             ON DELETE SET NULL -- Eğer bir bölüm silinirse, o bölümün koordinatörünün bölüm bilgisi NULL olur.
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Tablo 3: `classrooms` (Derslikler)
-- Her bölümün kendi dersliklerini tanımladığı tablodur.
-- Kapasite ve oturma düzeni bilgileri sınav optimizasyonu için kritiktir.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS classrooms (
                                          id INT NOT NULL AUTO_INCREMENT,
                                          department_id INT NOT NULL,
                                          code VARCHAR(50) NOT NULL,
                                          name VARCHAR(255) NOT NULL,
                                          capacity INT NOT NULL,
                                          rows_count INT NOT NULL, -- Boyuna Sıra Sayısı (satır)
                                          cols_count INT NOT NULL, -- Enine Sıra Sayısı (sütun)
                                          seating_type INT NOT NULL, -- Sıra yapısı (Örn: 2'li veya 3'lü)
                                          PRIMARY KEY (id),
                                          CONSTRAINT fk_classrooms_departments
                                              FOREIGN KEY (department_id)
                                                  REFERENCES departments(id)
                                                  ON DELETE CASCADE -- Eğer bir bölüm silinirse, o bölüme ait tüm derslikler de silinir.
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Tablo 4: `instructors` (Öğretim Üyeleri)
-- Excel'den derslerle birlikte okunacak olan öğretim üyelerini saklar.
-- `full_name` UNIQUE'dir, böylece aynı hoca tekrar tekrar eklenmez.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS instructors (
                                           id INT NOT NULL AUTO_INCREMENT,
                                           full_name VARCHAR(255) NOT NULL UNIQUE,
                                           PRIMARY KEY (id)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Tablo 5: `courses` (Dersler)
-- Excel'den okunacak olan ders bilgilerini saklar.
-- Her ders bir bölüme ve bir öğretim üyesine bağlıdır.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
                                       id INT NOT NULL AUTO_INCREMENT,
                                       department_id INT NOT NULL,
                                       instructor_id INT NOT NULL,
                                       code VARCHAR(50) NOT NULL UNIQUE,
                                       name VARCHAR(255) NOT NULL,
                                       course_type ENUM('Zorunlu', 'Seçmeli') NOT NULL,
                                       class_level INT NOT NULL, -- Dersin hangi sınıfa ait olduğu (Örn: 1, 2, 3, 4)
                                       PRIMARY KEY (id),
                                       CONSTRAINT fk_courses_departments
                                           FOREIGN KEY (department_id)
                                               REFERENCES departments(id)
                                               ON DELETE CASCADE,
                                       CONSTRAINT fk_courses_instructors
                                           FOREIGN KEY (instructor_id)
                                               REFERENCES instructors(id)
                                               ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Tablo 6: `students` (Öğrenciler)
-- Excel'den okunacak olan öğrenci bilgilerini saklar.
-- `student_no` UNIQUE'dir, böylece aynı öğrenci tekrar eklenmez.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
                                        id INT NOT NULL AUTO_INCREMENT,
                                        student_no VARCHAR(100) NOT NULL UNIQUE,
                                        full_name VARCHAR(255) NOT NULL,
                                        class_level INT NOT NULL, -- Öğrencinin sınıfı
                                        PRIMARY KEY (id)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Tablo 7: `enrollments` (Ders Kayıtları)
-- Hangi öğrencinin hangi dersi aldığını gösteren ilişki tablosu (Many-to-Many).
-- Sınav çakışmalarını kontrol etmek için bu tablo kullanılır.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS enrollments (
                                           student_id INT NOT NULL,
                                           course_id INT NOT NULL,
                                           PRIMARY KEY (student_id, course_id),
                                           CONSTRAINT fk_enrollments_students
                                               FOREIGN KEY (student_id)
                                                   REFERENCES students(id)
                                                   ON DELETE CASCADE,
                                           CONSTRAINT fk_enrollments_courses
                                               FOREIGN KEY (course_id)
                                                   REFERENCES courses(id)
                                                   ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Tablo 8: `exams` (Sınavlar)
-- Sınav oluşturma algoritmasının ürettiği ana sınav programını saklar.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS exams (
                                     id INT NOT NULL AUTO_INCREMENT,
                                     course_id INT NOT NULL,
                                     exam_type ENUM('Vize', 'Final', 'Bütünleme') NOT NULL,
                                     exam_date DATE NOT NULL,
                                     start_time TIME NOT NULL,
                                     duration_minutes INT NOT NULL,
                                     PRIMARY KEY (id),
                                     CONSTRAINT fk_exams_courses
                                         FOREIGN KEY (course_id)
                                             REFERENCES courses(id)
                                             ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Tablo 9: `exam_assignments` (Sınav Atamaları)
-- Bir sınavın hangi derslik veya dersliklerde yapılacağını belirten ilişki tablosu.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS exam_assignments (
                                                exam_id INT NOT NULL,
                                                classroom_id INT NOT NULL,
                                                PRIMARY KEY (exam_id, classroom_id),
                                                CONSTRAINT fk_exam_assignments_exams
                                                    FOREIGN KEY (exam_id)
                                                        REFERENCES exams(id)
                                                        ON DELETE CASCADE,
                                                CONSTRAINT fk_exam_assignments_classrooms
                                                    FOREIGN KEY (classroom_id)
                                                        REFERENCES classrooms(id)
                                                        ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Tablo 10: `seating_assignments` (Oturma Planı)
-- Oluşturulan bir sınavda, her öğrencinin hangi derslikte ve hangi sırada
-- oturacağını saklayan detaylı tablodur.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS seating_assignments (
                                                   id INT NOT NULL AUTO_INCREMENT,
                                                   exam_id INT NOT NULL,
                                                   student_id INT NOT NULL,
                                                   classroom_id INT NOT NULL,
                                                   seat_row INT NOT NULL,
                                                   seat_col INT NOT NULL,
                                                   PRIMARY KEY (id),
                                                   UNIQUE KEY unique_seat_per_exam (exam_id, classroom_id, seat_row, seat_col), -- Bir sınavda aynı koltuğa sadece bir öğrenci oturabilir.
                                                   UNIQUE KEY unique_student_per_exam (exam_id, student_id), -- Bir öğrenci bir sınavda sadece bir koltukta olabilir.
                                                   CONSTRAINT fk_seating_exams
                                                       FOREIGN KEY (exam_id)
                                                           REFERENCES exams(id)
                                                           ON DELETE CASCADE,
                                                   CONSTRAINT fk_seating_students
                                                       FOREIGN KEY (student_id)
                                                           REFERENCES students(id)
                                                           ON DELETE CASCADE,
                                                   CONSTRAINT fk_seating_classrooms
                                                       FOREIGN KEY (classroom_id)
                                                           REFERENCES classrooms(id)
                                                           ON DELETE CASCADE
) ENGINE=InnoDB;


-- -----------------------------------------------------
-- Adım 3: Başlangıç Verilerinin Eklenmesi
-- -----------------------------------------------------

-- Projede istenen 5 bölümü ekleyelim.
INSERT INTO departments (name) VALUES
                                   ('Bilgisayar Mühendisliği'),
                                   ('Yazılım Mühendisliği'),
                                   ('Elektrik Mühendisliği'),
                                   ('Elektronik Mühendisliği'),
                                   ('İnşaat Mühendisliği')
ON DUPLICATE KEY UPDATE name=name; -- Eğer zaten varsa ekleme

-- Projede istenen default Admin kullanıcısını ekleyelim.
-- Şifre: 'admin123' (Uygulama kodunda bu şifreyi kontrol edeceksiniz)
INSERT INTO users (email, password, role, department_id) VALUES
    ('admin@kocaeli.edu.tr', 'admin123', 'admin', NULL)
ON DUPLICATE KEY UPDATE email=email;

-- Bilgisayar Mühendisliği Bölümü için örnek derslikler ekle
-- Bölüm ID'si 1 (Bilgisayar Mühendisliği)
INSERT INTO classrooms (department_id, code, name, capacity, rows_count, cols_count, seating_type) VALUES
    (1, '3001', '301', 42, 7, 3, 3),
    (1, '3002', 'Büyük Amfi', 48, 8, 3, 4),
    (1, '3003', '303', 42, 7, 3, 3),
    (1, '3004', 'EDA', 30, 6, 5, 2),
    (1, '3005', '305', 42, 7, 3, 3)
ON DUPLICATE KEY UPDATE code=code;

-- Diğer bölümler için örnek derslikler
-- Yazılım Mühendisliği (ID: 2)
INSERT INTO classrooms (department_id, code, name, capacity, rows_count, cols_count, seating_type) VALUES
    (2, '4001', 'YZM-101', 40, 8, 5, 2),
    (2, '4002', 'YZM-102', 35, 7, 5, 2),
    (2, '4003', 'YZM-Lab', 30, 6, 5, 2)
ON DUPLICATE KEY UPDATE code=code;

-- Elektrik Mühendisliği (ID: 3)
INSERT INTO classrooms (department_id, code, name, capacity, rows_count, cols_count, seating_type) VALUES
    (3, '5001', 'ELK-201', 45, 9, 5, 2),
    (3, '5002', 'ELK-202', 40, 8, 5, 2),
    (3, '5003', 'ELK-Lab', 25, 5, 5, 2)
ON DUPLICATE KEY UPDATE code=code;

-- Elektronik Mühendisliği (ID: 4)
INSERT INTO classrooms (department_id, code, name, capacity, rows_count, cols_count, seating_type) VALUES
    (4, '6001', 'ELT-301', 38, 7, 5, 2),
    (4, '6002', 'ELT-302', 42, 7, 6, 2),
    (4, '6003', 'ELT-Lab', 28, 7, 4, 2)
ON DUPLICATE KEY UPDATE code=code;

-- İnşaat Mühendisliği (ID: 5)
INSERT INTO classrooms (department_id, code, name, capacity, rows_count, cols_count, seating_type) VALUES
    (5, '7001', 'İNŞ-101', 50, 10, 5, 2),
    (5, '7002', 'İNŞ-102', 45, 9, 5, 2),
    (5, '7003', 'İNŞ-Proje', 35, 7, 5, 2)
ON DUPLICATE KEY UPDATE code=code;

ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '145323';
FLUSH PRIVILEGES;

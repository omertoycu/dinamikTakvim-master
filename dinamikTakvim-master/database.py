# database.py
# Veritabanı bağlantısı ve sorgu işlemlerini yönetir.

import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG # Yapılandırma dosyasından bağlantı bilgilerini al

def get_db_connection():
    """Veritabanına yeni bir bağlantı oluşturur ve döndürür."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

def verify_user(email, password):
    """Verilen e-posta ve şifre ile kullanıcıyı doğrular."""
    from password_utils import verify_password, is_legacy_password
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # LEFT JOIN ile bölüm adını da alıyoruz, giriş yapan koordinatörün panelinde bölüm adı göstermek için.
            query = """
                SELECT u.*, d.name as department_name 
                FROM users u 
                LEFT JOIN departments d ON u.department_id = d.id 
                WHERE u.email = %s
            """
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            
            if user:
                # Şifre doğrulaması
                stored_password = user['password']
                
                # Yeni hash'li şifre kontrolü
                if verify_password(password, stored_password):
                    return user
                # Eski düz metin şifre kontrolü (geçiş için)
                elif is_legacy_password(password, stored_password):
                    # Şifreyi hash'le ve güncelle
                    from password_utils import hash_password
                    new_hashed_password = hash_password(password)
                    update_user_password(user['id'], new_hashed_password)
                    return user
            
            return None
        except Error as e:
            print(f"Kullanıcı doğrulanırken hata oluştu: {e}")
            return None
        finally:
            connection.close()
    return None

def update_user_password(user_id, hashed_password):
    """Kullanıcının şifresini günceller."""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        query = "UPDATE users SET password = %s WHERE id = %s"
        cursor.execute(query, (hashed_password, user_id))
        connection.commit()
        return True
    except Error as e:
        print(f"Şifre güncellenirken hata: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

# --- ADMIN DASHBOARD İÇİN FONKSİYONLAR ---

def get_all_departments():
    """Veritabanındaki tüm bölümleri ID'leri ve isimleriyle birlikte alır."""
    departments = []
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM departments ORDER BY name")
            departments = cursor.fetchall()
        except Error as e:
            print(f"Departmanlar alınırken hata oluştu: {e}")
        finally:
            cursor.close()
            connection.close()
    return departments

def get_all_users():
    """Veritabanındaki tüm kullanıcıları rolleri ve bölümleriyle birlikte alır."""
    users = []
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT u.id, u.email, u.role, d.name as department_name
                FROM users u
                LEFT JOIN departments d ON u.department_id = d.id
                ORDER BY u.role, u.email
            """
            cursor.execute(query)
            users = cursor.fetchall()
        except Error as e:
            print(f"Kullanıcılar alınırken hata oluştu: {e}")
        finally:
            cursor.close()
            connection.close()
    return users

def add_new_user(email, password, role, department_id):
    """Veritabanına yeni bir kullanıcı ekler."""
    from password_utils import hash_password
    
    connection = get_db_connection()
    if not connection:
        return False, "Veritabanı bağlantısı kurulamadı."
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return False, "Bu e-posta adresi zaten kayıtlı."
        if role == 'admin':
            department_id = None
        
        # Şifreyi hash'le
        hashed_password = hash_password(password)
        
        query = "INSERT INTO users (email, password, role, department_id) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (email, hashed_password, role, department_id))
        connection.commit()
        return True, "Kullanıcı başarıyla eklendi."
    except Error as e:
        print(f"Kullanıcı eklenirken hata oluştu: {e}")
        return False, f"Veritabanı hatası: {e}"
    finally:
        cursor.close()
        connection.close()

# --- COORDINATOR DASHBOARD İÇİN YENİ FONKSİYONLAR ---

def get_classrooms_by_department(department_id):
    """Belirli bir bölüme ait tüm derslikleri listeler."""
    classrooms = []
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM classrooms WHERE department_id = %s ORDER BY code"
            cursor.execute(query, (department_id,))
            classrooms = cursor.fetchall()
        except Error as e:
            print(f"Derslikler alınırken hata oluştu: {e}")
        finally:
            cursor.close()
            connection.close()
    return classrooms

def add_classroom(data):
    """Veritabanına yeni bir derslik ekler."""
    connection = get_db_connection()
    if not connection: return False, "Veritabanı bağlantısı kurulamadı."
    try:
        cursor = connection.cursor()
        # Aynı bölümde aynı kodlu derslik var mı kontrol et
        cursor.execute("SELECT id FROM classrooms WHERE department_id = %s AND code = %s", 
                      (data['department_id'], data['code']))
        if cursor.fetchone():
            return False, f"Bu bölümde '{data['code']}' kodlu derslik zaten mevcut."
        
        query = """
            INSERT INTO classrooms (department_id, code, name, capacity, rows_count, cols_count, seating_type)
            VALUES (%(department_id)s, %(code)s, %(name)s, %(capacity)s, %(rows_count)s, %(cols_count)s, %(seating_type)s)
        """
        cursor.execute(query, data)
        connection.commit()
        return True, "Derslik başarıyla eklendi."
    except Error as e:
        return False, f"Derslik eklenirken hata: {e}"
    finally:
        cursor.close()
        connection.close()

def update_classroom(classroom_id, data):
    """Mevcut bir dersliğin bilgilerini günceller."""
    connection = get_db_connection()
    if not connection: return False, "Veritabanı bağlantısı kurulamadı."
    try:
        cursor = connection.cursor()
        # Aynı bölümde aynı kodlu başka derslik var mı kontrol et (kendisi hariç)
        cursor.execute("SELECT id FROM classrooms WHERE department_id = %s AND code = %s AND id != %s", 
                      (data['department_id'], data['code'], classroom_id))
        if cursor.fetchone():
            return False, f"Bu bölümde '{data['code']}' kodlu başka bir derslik zaten mevcut."
        
        data['id'] = classroom_id
        query = """
            UPDATE classrooms SET 
            code = %(code)s, name = %(name)s, capacity = %(capacity)s, 
            rows_count = %(rows_count)s, cols_count = %(cols_count)s, seating_type = %(seating_type)s
            WHERE id = %(id)s
        """
        cursor.execute(query, data)
        connection.commit()
        return True, "Derslik başarıyla güncellendi."
    except Error as e:
        return False, f"Derslik güncellenirken hata: {e}"
    finally:
        cursor.close()
        connection.close()

def delete_classroom(classroom_id):
    """Veritabanından bir dersliği siler."""
    connection = get_db_connection()
    if not connection: return False, "Veritabanı bağlantısı kurulamadı."
    try:
        cursor = connection.cursor()
        query = "DELETE FROM classrooms WHERE id = %s"
        cursor.execute(query, (classroom_id,))
        connection.commit()
        return True, "Derslik başarıyla silindi."
    except Error as e:
        return False, f"Derslik silinirken hata: {e}"
    finally:
        cursor.close()
        connection.close()

def get_classroom_details(classroom_id, department_id):
    """Arama ve görselleştirme için tek bir dersliğin detaylarını alır."""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # department_id kontrolü, koordinatörün başka bölüm dersliğini görmesini engeller
            query = "SELECT * FROM classrooms WHERE id = %s AND department_id = %s"
            cursor.execute(query, (classroom_id, department_id))
            classroom = cursor.fetchone()
            return classroom
        except Error as e:
            print(f"Derslik detayı alınırken hata: {e}")
            return None
        finally:
            connection.close()
    return None

# --- EXCEL İÇE AKTARMA FONKSİYONLARI ---

def add_instructor(full_name):
    """Yeni bir öğretim üyesi ekler. Eğer zaten varsa ID'sini döndürür."""
    connection = get_db_connection()
    if not connection: return None, "Veritabanı bağlantısı kurulamadı."
    try:
        cursor = connection.cursor()
        # Önce var mı kontrol et
        cursor.execute("SELECT id FROM instructors WHERE full_name = %s", (full_name,))
        existing = cursor.fetchone()
        if existing:
            return existing[0], "Öğretim üyesi zaten mevcut."
        # Yoksa ekle
        cursor.execute("INSERT INTO instructors (full_name) VALUES (%s)", (full_name,))
        connection.commit()
        return cursor.lastrowid, "Öğretim üyesi eklendi."
    except Error as e:
        return None, f"Öğretim üyesi eklenirken hata: {e}"
    finally:
        cursor.close()
        connection.close()

def add_course(department_id, instructor_id, code, name, course_type, class_level):
    """Yeni bir ders ekler."""
    connection = get_db_connection()
    if not connection: return None, "Veritabanı bağlantısı kurulamadı."
    try:
        cursor = connection.cursor()
        # Aynı kodlu ders var mı kontrol et
        cursor.execute("SELECT id FROM courses WHERE code = %s", (code,))
        existing = cursor.fetchone()
        if existing:
            # Mevcut dersi hata saymayalım; id döndürüp mesaj verelim
            return existing[0], f"Ders kodu '{code}' zaten mevcut."
        cursor.execute("""
            INSERT INTO courses (department_id, instructor_id, code, name, course_type, class_level) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (department_id, instructor_id, code, name, course_type, class_level))
        connection.commit()
        return cursor.lastrowid, "Ders eklendi."
    except Error as e:
        return None, f"Ders eklenirken hata: {e}"
    finally:
        cursor.close()
        connection.close()

def sanitize_courses(department_id):
    """Hatalı eklenmiş dersleri temizler ve sınıf seviyelerini koddan türetir."""
    connection = get_db_connection()
    if not connection: return False, "Veritabanı bağlantısı kurulamadı."
    try:
        cursor = connection.cursor()
        
        # 1) Başlık/sınıf satırı gibi yanlış ders kayıtlarını sil
        cursor.execute(
            """DELETE FROM courses 
               WHERE department_id = %s AND (
                   code = 'DERS KODU' OR 
                   code LIKE '%%Sınıf%%' OR 
                   name IS NULL OR 
                   name = '' OR
                   code = 'nan' OR
                   name = 'nan' OR
                   code LIKE 'SEÇMELİ DERS%%' OR
                   name LIKE 'SEÇMELİ DERS%%' OR
                   code LIKE 'ZORUNLU DERS%%' OR
                   name LIKE 'ZORUNLU DERS%%' OR
                   LENGTH(code) < 3 OR
                   LENGTH(name) < 3
               )""",
            (department_id,)
        )
        deleted_count = cursor.rowcount
        
        # 2) Sınıf seviyesini ders kodundan türet (ilk rakam)
        cursor.execute(
            """
            UPDATE courses
            SET class_level = 
                CASE 
                    WHEN code REGEXP '[0-9]' THEN CAST(SUBSTRING(code, REGEXP_INSTR(code, '[0-9]'), 1) AS UNSIGNED)
                    ELSE class_level
                END
            WHERE department_id = %s
            """,
            (department_id,)
        )
        updated_count = cursor.rowcount
        
        connection.commit()
        return True, f"Ders kayıtları temizlendi ({deleted_count} geçersiz kayıt silindi) ve {updated_count} ders güncellendi."
    except Error as e:
        return False, f"Temizleme/güncelleme hatası: {e}"
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        connection.close()

def add_student(student_no, full_name, class_level):
    """Yeni bir öğrenci ekler."""
    connection = get_db_connection()
    if not connection: return None, "Veritabanı bağlantısı kurulamadı."
    try:
        cursor = connection.cursor()
        # Aynı öğrenci no var mı kontrol et
        cursor.execute("SELECT id FROM students WHERE student_no = %s", (student_no,))
        existing = cursor.fetchone()
        if existing:
            return existing[0], "Öğrenci zaten mevcut."
        cursor.execute("INSERT INTO students (student_no, full_name, class_level) VALUES (%s, %s, %s)", 
                      (student_no, full_name, class_level))
        connection.commit()
        return cursor.lastrowid, "Öğrenci eklendi."
    except Error as e:
        return None, f"Öğrenci eklenirken hata: {e}"
    finally:
        cursor.close()
        connection.close()

def add_enrollment(student_id, course_id):
    """Öğrenci-ders kaydı oluşturur."""
    connection = get_db_connection()
    if not connection: return False, "Veritabanı bağlantısı kurulamadı."
    try:
        cursor = connection.cursor()
        # Zaten kayıtlı mı kontrol et
        cursor.execute("SELECT 1 FROM enrollments WHERE student_id = %s AND course_id = %s", 
                      (student_id, course_id))
        if cursor.fetchone():
            return True, "Kayıt zaten mevcut."
        cursor.execute("INSERT INTO enrollments (student_id, course_id) VALUES (%s, %s)", 
                      (student_id, course_id))
        connection.commit()
        return True, "Kayıt oluşturuldu."
    except Error as e:
        return False, f"Kayıt oluşturulurken hata: {e}"
    finally:
        cursor.close()
        connection.close()

def get_course_by_code(code):
    """Ders koduna göre ders bilgilerini getirir."""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM courses WHERE code = %s", (code,))
            return cursor.fetchone()
        except Error as e:
            print(f"Ders bilgisi alınırken hata: {e}")
            return None
        finally:
            connection.close()
    return None

def get_student_by_no(student_no):
    """Öğrenci numarasına göre öğrenci bilgilerini getirir."""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM students WHERE student_no = %s", (student_no,))
            return cursor.fetchone()
        except Error as e:
            print(f"Öğrenci bilgisi alınırken hata: {e}")
            return None
        finally:
            connection.close()
    return None


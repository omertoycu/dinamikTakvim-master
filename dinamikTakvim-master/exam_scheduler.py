# exam_scheduler.py
# Sınav zamanlama algoritmasını içerir.

from datetime import datetime, timedelta, date, time
from database import get_db_connection
import random

class ExamScheduler:
    """Sınav zamanlama algoritmasını yöneten sınıf."""
    
    def __init__(self, department_id):
        self.department_id = department_id
        self.exam_dates = []
        self.exam_times = [
            time(9, 0),   # 09:00
            time(11, 0),  # 11:00
            time(13, 0),  # 13:00
            time(15, 0),  # 15:00
        ]
        self.exam_duration = 120  # 2 saat
        self.course_students_cache = {}  # Performans için önbellek
        
    def generate_exam_schedule(self, start_date, end_date, exam_types=['Vize', 'Final'], constraints=None):
        """
        Sınav programını oluşturur.
        
        Args:
            start_date: Sınav döneminin başlangıç tarihi
            end_date: Sınav döneminin bitiş tarihi
            exam_types: Sınav türleri listesi
            constraints: Kısıtlar sözlüğü (ders seçimi, süreler, vb.)
        """
        try:
            # Mevcut sınavları temizle
            self.clear_existing_exams()
            
            # Kısıtları işle
            if constraints is None:
                constraints = {}
            
            default_duration = constraints.get('default_duration', 120)
            waiting_time = constraints.get('waiting_time', 15)
            no_overlap = constraints.get('no_overlap', False)
            excluded_days = constraints.get('excluded_days', [5, 6])  # Cumartesi, Pazar
            selected_courses = constraints.get('selected_courses', [])
            course_durations = constraints.get('course_durations', {})
            
            # Tarih aralığını oluştur
            self.exam_dates = self._generate_date_range(start_date, end_date, excluded_days)
            
            if not self.exam_dates:
                return {
                    'success': False,
                    'message': "Seçilen tarih aralığında uygun gün bulunamadı!",
                    'scheduled_count': 0
                }
            
            # Dersleri ve öğrenci sayılarını al
            all_courses = self._get_courses_with_student_counts()
            
            # Seçili dersleri filtrele
            if selected_courses:
                courses = [c for c in all_courses if c['id'] in selected_courses]
            else:
                courses = all_courses
            
            if not courses:
                return {
                    'success': False,
                    'message': "Zamanlanacak ders bulunamadı!",
                    'scheduled_count': 0
                }
            
            # PERFORMANS İYİLEŞTİRMESİ: Tüm ders-öğrenci eşleşmelerini önceden yükle
            print("Ders-öğrenci eşleşmeleri yükleniyor...")
            self.course_students_cache = {}
            for course in courses:
                self.course_students_cache[course['id']] = self._get_course_students(course['id'])
            
            # Sınavları zamanla
            scheduled_exams = []
            warnings = []
            errors = []
            
            for exam_type in exam_types:
                for course in courses:
                    # Ders için süre belirle
                    exam_duration = course_durations.get(course['id'], default_duration)
                    
                    # Uygun slot bul
                    exam_slot = self._find_available_slot(
                        course, exam_type, scheduled_exams, 
                        no_overlap, waiting_time
                    )
                    
                    if exam_slot:
                        exam_id = self._create_exam(course, exam_type, exam_slot, exam_duration)
                        if exam_id:
                            # Dersliklere atama yap
                            assignment_success = self._assign_to_classrooms(exam_id, course['student_count'])
                            if not assignment_success:
                                warnings.append(f"⚠️ {course['code']} dersi için yeterli derslik bulunamadı")
                            
                            scheduled_exams.append({
                                'exam_id': exam_id,
                                'course_id': course['id'],
                                'course_code': course['code'],
                                'class_level': course['class_level'],
                                'date': exam_slot['date'],
                                'time': exam_slot['time'],
                                'student_count': course['student_count']
                            })
                        else:
                            errors.append(f"❌ {course['code']} dersi için sınav oluşturulamadı")
                    else:
                        errors.append(f"❌ {course['code']} - {exam_type} için uygun zaman bulunamadı (çakışma var)")
            
            # Cache'i temizle
            self.course_students_cache = {}
            
            return {
                'success': True,
                'message': f"✅ {len(scheduled_exams)} sınav başarıyla zamanlandı.",
                'scheduled_count': len(scheduled_exams),
                'warnings': warnings,
                'errors': errors
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f"❌ Sınav zamanlama hatası: {str(e)}",
                'scheduled_count': 0
            }
    
    def _generate_date_range(self, start_date, end_date, excluded_days=None):
        """Tarih aralığını oluşturur (belirtilen günler hariç)."""
        if excluded_days is None:
            excluded_days = [5, 6]  # Varsayılan: Cumartesi, Pazar
        
        dates = []
        current = start_date
        while current <= end_date:
            # Hariç tutulan günler dışındaki günleri ekle
            if current.weekday() not in excluded_days:
                dates.append(current)
            current += timedelta(days=1)
        return dates
    
    def _get_courses_with_student_counts(self):
        """Dersleri ve öğrenci sayılarını getirir."""
        connection = get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT c.id, c.code, c.name, c.class_level, 
                       COUNT(e.student_id) as student_count
                FROM courses c
                LEFT JOIN enrollments e ON c.id = e.course_id
                WHERE c.department_id = %s
                GROUP BY c.id, c.code, c.name, c.class_level
                ORDER BY c.class_level, c.code
            """
            cursor.execute(query, (self.department_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Dersler alınırken hata: {e}")
            return []
        finally:
            connection.close()
    
    def _find_available_slot(self, course, exam_type, scheduled_exams, no_overlap=False, waiting_time=15):
        """Ders için uygun zaman dilimi bulur (öğrenci çakışma kontrolü ile)."""
        # Bu dersi alan öğrencileri al (cache'den)
        course_students = self.course_students_cache.get(course['id'], [])
        
        if not course_students:
            # Öğrencisi olmayan dersler için basit zamanlama
            for date in self.exam_dates:
                for time_slot in self.exam_times:
                    if no_overlap:
                        conflict = any(s['date'] == date and s['time'] == time_slot for s in scheduled_exams)
                        if not conflict:
                            return {'date': date, 'time': time_slot}
                    else:
                        return {'date': date, 'time': time_slot}
            return None
        
        for date in self.exam_dates:
            for time_slot in self.exam_times:
                conflict = False
                
                # 1. Hiçbir sınav aynı anda olmaması kısıtı
                if no_overlap:
                    for scheduled in scheduled_exams:
                        if (scheduled['date'] == date and 
                            scheduled['time'] == time_slot):
                            conflict = True
                            break
                    
                    if conflict:
                        continue
                
                # 2. Öğrenci bazlı çakışma kontrolü (cache'den)
                for student_id in course_students:
                    if self._student_has_exam_at_cached(student_id, date, time_slot, scheduled_exams):
                        conflict = True
                        break
                
                if conflict:
                    continue
                
                # 3. Bekleme süresi kontrolü (sadece waiting_time > 0 ise)
                if waiting_time > 0:
                    for student_id in course_students:
                        if not self._check_waiting_time_cached(student_id, date, time_slot, scheduled_exams, waiting_time):
                            conflict = True
                            break
                
                if not conflict:
                    return {
                        'date': date,
                        'time': time_slot
                    }
        
        return None
    
    def _get_course_students(self, course_id):
        """Derse kayıtlı öğrenci ID'lerini döndürür."""
        connection = get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor()
            query = "SELECT student_id FROM enrollments WHERE course_id = %s"
            cursor.execute(query, (course_id,))
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ders öğrencileri alınırken hata: {e}")
            return []
        finally:
            connection.close()
    
    def _student_has_exam_at_cached(self, student_id, date, time_slot, scheduled_exams):
        """Öğrencinin belirtilen tarih ve saatte sınavı var mı kontrol eder (cache kullanarak)."""
        for exam in scheduled_exams:
            if exam['date'] == date and exam['time'] == time_slot:
                # Bu sınavı alan öğrenciler arasında bu öğrenci var mı? (cache'den)
                exam_students = self.course_students_cache.get(exam['course_id'], [])
                if student_id in exam_students:
                    return True
        return False
    
    def _check_waiting_time_cached(self, student_id, date, time_slot, scheduled_exams, waiting_time):
        """Öğrencinin bekleme süresi kısıtını kontrol eder (cache kullanarak)."""
        # Aynı günde öğrencinin başka sınavları var mı?
        for exam in scheduled_exams:
            if exam['date'] == date:
                exam_students = self.course_students_cache.get(exam['course_id'], [])
                if student_id in exam_students:
                    # Saat farkını hesapla (basitleştirilmiş)
                    exam_time = exam['time']
                    slot_time = time_slot
                    
                    # time objelerini dakikaya çevir
                    exam_minutes = exam_time.hour * 60 + exam_time.minute
                    slot_minutes = slot_time.hour * 60 + slot_time.minute
                    
                    time_diff = abs(exam_minutes - slot_minutes)
                    
                    # Eğer bekleme süresinden az ise False döndür
                    if time_diff < waiting_time and time_diff > 0:
                        return False
        
        return True
    
    def _create_exam(self, course, exam_type, exam_slot, exam_duration=None):
        """Veritabanına sınav kaydı oluşturur."""
        if exam_duration is None:
            exam_duration = self.exam_duration
        
        connection = get_db_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                INSERT INTO exams (course_id, exam_type, exam_date, start_time, duration_minutes)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                course['id'], exam_type, exam_slot['date'], 
                exam_slot['time'], exam_duration
            ))
            connection.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Sınav oluşturulurken hata: {e}")
            return None
        finally:
            connection.close()
    
    def _assign_to_classrooms(self, exam_id, student_count):
        """Sınavı uygun dersliklere atar."""
        connection = get_db_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Bölüme ait derslikleri kapasiteye göre sırala
            query = """
                SELECT id, capacity FROM classrooms 
                WHERE department_id = %s 
                ORDER BY capacity DESC
            """
            cursor.execute(query, (self.department_id,))
            classrooms = cursor.fetchall()
            
            remaining_students = student_count
            assigned_classrooms = []

            # Dağıtımı çeşitlendirmek için başlangıç indeksini döndür (her sınav farklı dersten başlasın)
            start_index = 0
            try:
                # exam_id ile döndürme, aynı kapasite sırasına takılmayı azaltır
                start_index = exam_id % len(classrooms) if classrooms else 0
            except Exception:
                start_index = 0

            # Sıralı listeyi rotate et
            rotated_classrooms = classrooms[start_index:] + classrooms[:start_index]

            # Öğrencileri dersliklere dağıt
            for classroom in rotated_classrooms:
                if remaining_students <= 0:
                    break
                
                # Bu dersliğe kaç öğrenci sığar
                # Destek: tuple veya dict gelebilir
                capacity = classroom['capacity'] if isinstance(classroom, dict) else classroom[1]
                classroom_id = classroom['id'] if isinstance(classroom, dict) else classroom[0]
                students_in_this_classroom = min(remaining_students, capacity)
                
                # Sınav-derslik atamasını oluştur
                cursor.execute(
                    "INSERT INTO exam_assignments (exam_id, classroom_id) VALUES (%s, %s)",
                    (exam_id, classroom_id)
                )
                
                assigned_classrooms.append({
                    'classroom_id': classroom_id,
                    'student_count': students_in_this_classroom
                })
                
                remaining_students -= students_in_this_classroom
            
            connection.commit()
            return True
            
        except Exception as e:
            print(f"Derslik ataması yapılırken hata: {e}")
            return False
        finally:
            connection.close()
    
    def clear_existing_exams(self):
        """Mevcut sınavları temizler."""
        connection = get_db_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            
            # İlişkili tabloları temizle
            cursor.execute("DELETE FROM seating_assignments WHERE exam_id IN (SELECT id FROM exams WHERE course_id IN (SELECT id FROM courses WHERE department_id = %s))", (self.department_id,))
            cursor.execute("DELETE FROM exam_assignments WHERE exam_id IN (SELECT id FROM exams WHERE course_id IN (SELECT id FROM courses WHERE department_id = %s))", (self.department_id,))
            cursor.execute("DELETE FROM exams WHERE course_id IN (SELECT id FROM courses WHERE department_id = %s)", (self.department_id,))
            
            connection.commit()
            return True
        except Exception as e:
            print(f"Mevcut sınavlar temizlenirken hata: {e}")
            return False
        finally:
            connection.close()
    
    def get_scheduled_exams(self):
        """Zamanlanmış sınavları getirir."""
        connection = get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT e.id, e.exam_type, e.exam_date, e.start_time, e.duration_minutes,
                       c.code as course_code, c.name as course_name, c.class_level,
                       i.full_name as instructor_name
                FROM exams e
                JOIN courses c ON e.course_id = c.id
                JOIN instructors i ON c.instructor_id = i.id
                WHERE c.department_id = %s
                ORDER BY e.exam_date, e.start_time
            """
            cursor.execute(query, (self.department_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Sınavlar alınırken hata: {e}")
            return []
        finally:
            connection.close()

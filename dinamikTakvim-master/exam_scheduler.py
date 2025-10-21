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
        
    def generate_exam_schedule(self, start_date, end_date, exam_types=['Vize', 'Final']):
        """
        Sınav programını oluşturur.
        
        Args:
            start_date: Sınav döneminin başlangıç tarihi
            end_date: Sınav döneminin bitiş tarihi
            exam_types: Sınav türleri listesi
        """
        try:
            # Mevcut sınavları temizle
            self.clear_existing_exams()
            
            # Tarih aralığını oluştur
            self.exam_dates = self._generate_date_range(start_date, end_date)
            
            # Dersleri ve öğrenci sayılarını al
            courses = self._get_courses_with_student_counts()
            
            # Sınavları zamanla
            scheduled_exams = []
            for exam_type in exam_types:
                for course in courses:
                    exam_slot = self._find_available_slot(course, exam_type, scheduled_exams)
                    if exam_slot:
                        exam_id = self._create_exam(course, exam_type, exam_slot)
                        if exam_id:
                            # Dersliklere atama yap
                            self._assign_to_classrooms(exam_id, course['student_count'])
                            scheduled_exams.append({
                                'exam_id': exam_id,
                                'course_id': course['id'],
                                'class_level': course['class_level'],  # Sınıf seviyesini ekle
                                'date': exam_slot['date'],
                                'time': exam_slot['time'],
                                'student_count': course['student_count']
                            })
            
            return {
                'success': True,
                'message': f"{len(scheduled_exams)} sınav başarıyla zamanlandı.",
                'scheduled_count': len(scheduled_exams)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Sınav zamanlama hatası: {str(e)}",
                'scheduled_count': 0
            }
    
    def _generate_date_range(self, start_date, end_date):
        """Tarih aralığını oluşturur (hafta sonları hariç)."""
        dates = []
        current = start_date
        while current <= end_date:
            # Hafta sonları hariç (Pazartesi=0, Pazar=6)
            if current.weekday() < 5:
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
    
    def _find_available_slot(self, course, exam_type, scheduled_exams):
        """Ders için uygun zaman dilimi bulur."""
        # Aynı sınıf seviyesindeki derslerin çakışmaması için kontrol
        # (Farklı sınıf seviyelerindeki dersler aynı anda farklı dersliklerde sınav yapabilir)
        same_level_courses = [exam for exam in scheduled_exams 
                             if exam.get('class_level') == course['class_level']]
        
        for date in self.exam_dates:
            for time_slot in self.exam_times:
                # Sadece aynı sınıf seviyesinde çakışma var mı kontrol et
                conflict = False
                for scheduled in same_level_courses:
                    if (scheduled['date'] == date and 
                        scheduled['time'] == time_slot):
                        conflict = True
                        break
                
                if not conflict:
                    return {
                        'date': date,
                        'time': time_slot
                    }
        
        return None
    
    def _create_exam(self, course, exam_type, exam_slot):
        """Veritabanına sınav kaydı oluşturur."""
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
                exam_slot['time'], self.exam_duration
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

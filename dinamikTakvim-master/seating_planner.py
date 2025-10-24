# seating_planner.py
# Oturma planı üretimi ve yönetimi işlemlerini içerir.

from database import get_db_connection
import random

class SeatingPlanner:
    """Oturma planı üretimi ve yönetimi sınıfı."""
    
    def __init__(self, department_id):
        self.department_id = department_id
    
    def generate_seating_plans(self):
        """Tüm sınavlar için oturma planları oluşturur."""
        try:
            # Sınavları ve atandıkları derslikleri al
            exams_with_classrooms = self._get_exams_with_classrooms()
            
            results = {
                'success': 0,
                'errors': [],
                'warnings': []
            }
            
            for exam_data in exams_with_classrooms:
                try:
                    # Bu sınava kayıtlı öğrencileri al
                    students = self._get_exam_students(exam_data['exam_id'])
                    
                    if not students:
                        results['warnings'].append(f"Sınav {exam_data['exam_id']}: Kayıtlı öğrenci bulunamadı")
                        continue
                    
                    # Her derslik için oturma planı oluştur
                    for classroom_data in exam_data['classrooms']:
                        classroom_id = classroom_data['classroom_id']
                        max_students = classroom_data['max_students']
                        
                        # Bu dersliğe atanacak öğrencileri seç
                        classroom_students = students[:max_students]
                        students = students[max_students:]  # Kalan öğrenciler
                        
                        if classroom_students:
                            # Oturma planını oluştur
                            seating_plan = self._create_seating_plan(
                                exam_data['exam_id'], 
                                classroom_id, 
                                classroom_students,
                                classroom_data['rows_count'],
                                classroom_data['cols_count'],
                                classroom_data['seating_type']
                            )
                            
                            if seating_plan:
                                results['success'] += 1
                            else:
                                results['errors'].append(f"Sınav {exam_data['exam_id']}, Derslik {classroom_id}: Oturma planı oluşturulamadı")
                    
                except Exception as e:
                    results['errors'].append(f"Sınav {exam_data['exam_id']}: {str(e)}")
            
            return results
            
        except Exception as e:
            return {
                'success': 0,
                'errors': [f"Oturma planı oluşturma hatası: {str(e)}"],
                'warnings': []
            }
    
    def _get_exams_with_classrooms(self):
        """Sınavları ve atandıkları derslik bilgileriyle birlikte getirir."""
        connection = get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT e.id as exam_id, e.exam_type, e.exam_date, e.start_time,
                       c.code as course_code, c.name as course_name,
                       cl.id as classroom_id, cl.code as classroom_code, 
                       cl.name as classroom_name, cl.capacity, cl.rows_count, 
                       cl.cols_count, cl.seating_type
                FROM exams e
                JOIN courses c ON e.course_id = c.id
                JOIN exam_assignments ea ON e.id = ea.exam_id
                JOIN classrooms cl ON ea.classroom_id = cl.id
                WHERE c.department_id = %s
                ORDER BY e.exam_date, e.start_time, cl.capacity DESC
            """
            cursor.execute(query, (self.department_id,))
            raw_data = cursor.fetchall()
            
            # Verileri sınav bazında grupla
            exams_dict = {}
            for row in raw_data:
                exam_id = row['exam_id']
                if exam_id not in exams_dict:
                    exams_dict[exam_id] = {
                        'exam_id': exam_id,
                        'exam_type': row['exam_type'],
                        'exam_date': row['exam_date'],
                        'start_time': row['start_time'],
                        'course_code': row['course_code'],
                        'course_name': row['course_name'],
                        'classrooms': []
                    }
                
                exams_dict[exam_id]['classrooms'].append({
                    'classroom_id': row['classroom_id'],
                    'classroom_code': row['classroom_code'],
                    'classroom_name': row['classroom_name'],
                    'capacity': row['capacity'],
                    'rows_count': row['rows_count'],
                    'cols_count': row['cols_count'],
                    'seating_type': row['seating_type'],
                    'max_students': row['capacity']  # Başlangıçta kapasite kadar
                })
            
            return list(exams_dict.values())
            
        except Exception as e:
            print(f"Sınavlar alınırken hata: {e}")
            return []
        finally:
            connection.close()
    
    def _get_exam_students(self, exam_id):
        """Belirli bir sınava kayıtlı öğrencileri getirir."""
        connection = get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT s.id, s.student_no, s.full_name, s.class_level
                FROM students s
                JOIN enrollments e ON s.id = e.student_id
                JOIN courses c ON e.course_id = c.id
                JOIN exams ex ON c.id = ex.course_id
                WHERE ex.id = %s
                ORDER BY s.student_no
            """
            cursor.execute(query, (exam_id,))
            return cursor.fetchall()
            
        except Exception as e:
            print(f"Öğrenciler alınırken hata: {e}")
            return []
        finally:
            connection.close()
    
    def _create_seating_plan(self, exam_id, classroom_id, students, rows, cols, seating_type):
        """Belirli bir derslik için oturma planı oluşturur."""
        connection = get_db_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            
            # Mevcut oturma planını temizle
            cursor.execute("DELETE FROM seating_assignments WHERE exam_id = %s AND classroom_id = %s", 
                          (exam_id, classroom_id))
            
            # Öğrencileri karıştır (adil dağıtım için)
            shuffled_students = students.copy()
            random.shuffle(shuffled_students)
            
            # Oturma planını oluştur
            student_index = 0
            for row in range(rows):
                for col in range(cols):
                    if student_index < len(shuffled_students):
                        student = shuffled_students[student_index]
                        
                        # Oturma atamasını kaydet
                        cursor.execute("""
                            INSERT INTO seating_assignments 
                            (exam_id, student_id, classroom_id, seat_row, seat_col)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (exam_id, student['id'], classroom_id, row + 1, col + 1))
                        
                        student_index += 1
                    else:
                        break  # Tüm öğrenciler yerleştirildi
            
            connection.commit()
            return True
            
        except Exception as e:
            print(f"Oturma planı oluşturulurken hata: {e}")
            return False
        finally:
            connection.close()
    
    def get_seating_plan(self, exam_id, classroom_id=None):
        """Belirli bir sınav için oturma planını getirir."""
        connection = get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            if classroom_id:
                # Belirli bir derslik için
                query = """
                    SELECT sa.seat_row, sa.seat_col, s.student_no, s.full_name,
                           cl.code as classroom_code, cl.name as classroom_name
                    FROM seating_assignments sa
                    JOIN students s ON sa.student_id = s.id
                    JOIN classrooms cl ON sa.classroom_id = cl.id
                    WHERE sa.exam_id = %s AND sa.classroom_id = %s
                    ORDER BY sa.seat_row, sa.seat_col
                """
                cursor.execute(query, (exam_id, classroom_id))
            else:
                # Tüm derslikler için
                query = """
                    SELECT sa.seat_row, sa.seat_col, s.student_no, s.full_name,
                           cl.code as classroom_code, cl.name as classroom_name,
                           cl.id as classroom_id
                    FROM seating_assignments sa
                    JOIN students s ON sa.student_id = s.id
                    JOIN classrooms cl ON sa.classroom_id = cl.id
                    WHERE sa.exam_id = %s
                    ORDER BY cl.code, sa.seat_row, sa.seat_col
                """
                cursor.execute(query, (exam_id,))
            
            return cursor.fetchall()
            
        except Exception as e:
            print(f"Oturma planı alınırken hata: {e}")
            return []
        finally:
            connection.close()
    
    def clear_seating_plans(self):
        """Tüm oturma planlarını temizler."""
        connection = get_db_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            
            # Bölüme ait sınavların oturma planlarını temizle
            cursor.execute("""
                DELETE FROM seating_assignments 
                WHERE exam_id IN (
                    SELECT e.id FROM exams e
                    JOIN courses c ON e.course_id = c.id
                    WHERE c.department_id = %s
                )
            """, (self.department_id,))
            
            connection.commit()
            return True
            
        except Exception as e:
            print(f"Oturma planları temizlenirken hata: {e}")
            return False
        finally:
            connection.close()

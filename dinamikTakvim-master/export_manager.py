# export_manager.py
# PDF ve Excel dışa aktarma işlemlerini yönetir.

import pandas as pd
from datetime import datetime
from database import get_db_connection
from exam_scheduler import ExamScheduler
from seating_planner import SeatingPlanner

class ExportManager:
    """Dışa aktarma işlemlerini yöneten sınıf."""
    
    def __init__(self, department_id):
        self.department_id = department_id
    
    def export_schedule_to_excel(self, file_path):
        """Sınav programını Excel dosyasına aktarır."""
        try:
            scheduler = ExamScheduler(self.department_id)
            exams = scheduler.get_scheduled_exams()
            
            if not exams:
                return False, "Dışa aktarılacak sınav bulunamadı."
            
            # Excel için veri hazırla
            excel_data = []
            for exam in exams:
                # Derslik bilgilerini al
                classroom_info = self._get_exam_classrooms(exam['id'])
                classroom_text = ", ".join([f"{c['code']}({c['capacity']})" for c in classroom_info])
                
                # MySQL TIME alanı timedelta olabilir
                start_time = exam['start_time']
                if hasattr(start_time, 'strftime'):
                    saat = start_time.strftime('%H:%M')
                else:
                    total_seconds = int(start_time.total_seconds())
                    saat = f"{(total_seconds // 3600) % 24:02d}:{(total_seconds % 3600) // 60:02d}"
                excel_data.append({
                    'Tarih': exam['exam_date'].strftime('%d.%m.%Y'),
                    'Saat': saat,
                    'Sınav Türü': exam['exam_type'],
                    'Ders Kodu': exam['course_code'],
                    'Ders Adı': exam['course_name'],
                    'Sınıf': exam['class_level'],
                    'Öğretim Üyesi': exam['instructor_name'],
                    'Derslikler': classroom_text
                })
            
            # DataFrame oluştur ve Excel'e yaz
            df = pd.DataFrame(excel_data)
            df.to_excel(file_path, index=False, sheet_name='Sınav Programı')
            
            return True, f"Sınav programı başarıyla Excel dosyasına aktarıldı: {file_path}"
            
        except Exception as e:
            return False, f"Excel dışa aktarma hatası: {str(e)}"
    
    def export_seating_plans_to_excel(self, file_path):
        """Oturma planlarını Excel dosyasına aktarır."""
        try:
            planner = SeatingPlanner(self.department_id)
            scheduler = ExamScheduler(self.department_id)
            exams = scheduler.get_scheduled_exams()
            
            if not exams:
                return False, "Dışa aktarılacak sınav bulunamadı."
            
            # Excel için veri hazırla
            excel_data = []
            for exam in exams:
                seating_data = planner.get_seating_plan(exam['id'])
                for seat in seating_data:
                    # TIME alanı timedelta olabilir
                    start_time = exam['start_time']
                    if hasattr(start_time, 'strftime'):
                        saat = start_time.strftime('%H:%M')
                    else:
                        total_seconds = int(start_time.total_seconds())
                        saat = f"{(total_seconds // 3600) % 24:02d}:{(total_seconds % 3600) // 60:02d}"
                    excel_data.append({
                        'Sınav': f"{exam['course_code']} - {exam['exam_type']}",
                        'Tarih': exam['exam_date'].strftime('%d.%m.%Y'),
                        'Saat': saat,
                        'Derslik': seat['classroom_code'],
                        'Sıra': seat['seat_row'],
                        'Sütun': seat['seat_col'],
                        'Öğrenci No': seat['student_no'],
                        'Ad Soyad': seat['full_name']
                    })
            
            if not excel_data:
                return False, "Dışa aktarılacak oturma planı bulunamadı."
            
            # DataFrame oluştur ve Excel'e yaz
            df = pd.DataFrame(excel_data)
            df.to_excel(file_path, index=False, sheet_name='Oturma Planları')
            
            return True, f"Oturma planları başarıyla Excel dosyasına aktarıldı: {file_path}"
            
        except Exception as e:
            return False, f"Excel dışa aktarma hatası: {str(e)}"
    
    def export_comprehensive_report_to_excel(self, file_path):
        """Kapsamlı raporu Excel dosyasına aktarır (birden fazla sayfa)."""
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 1. Sınav Programı
                self._export_schedule_sheet(writer)
                
                # 2. Oturma Planları
                self._export_seating_sheet(writer)
                
                # 3. Derslik Kullanımı
                self._export_classroom_usage_sheet(writer)
                
                # 4. Öğrenci Sınav Listesi
                self._export_student_exam_sheet(writer)
            
            return True, f"Kapsamlı rapor başarıyla Excel dosyasına aktarıldı: {file_path}"
            
        except Exception as e:
            return False, f"Excel dışa aktarma hatası: {str(e)}"
    
    def _export_schedule_sheet(self, writer):
        """Sınav programı sayfasını oluşturur."""
        scheduler = ExamScheduler(self.department_id)
        exams = scheduler.get_scheduled_exams()
        
        if exams:
            excel_data = []
            for exam in exams:
                classroom_info = self._get_exam_classrooms(exam['id'])
                classroom_text = ", ".join([f"{c['code']}({c['capacity']})" for c in classroom_info])
                
                start_time = exam['start_time']
                if hasattr(start_time, 'strftime'):
                    saat = start_time.strftime('%H:%M')
                else:
                    total_seconds = int(start_time.total_seconds())
                    saat = f"{(total_seconds // 3600) % 24:02d}:{(total_seconds % 3600) // 60:02d}"
                excel_data.append({
                    'Tarih': exam['exam_date'].strftime('%d.%m.%Y'),
                    'Saat': saat,
                    'Sınav Türü': exam['exam_type'],
                    'Ders Kodu': exam['course_code'],
                    'Ders Adı': exam['course_name'],
                    'Sınıf': exam['class_level'],
                    'Öğretim Üyesi': exam['instructor_name'],
                    'Derslikler': classroom_text
                })
            
            df = pd.DataFrame(excel_data)
            df.to_excel(writer, sheet_name='Sınav Programı', index=False)
    
    def _export_seating_sheet(self, writer):
        """Oturma planları sayfasını oluşturur."""
        planner = SeatingPlanner(self.department_id)
        scheduler = ExamScheduler(self.department_id)
        exams = scheduler.get_scheduled_exams()
        
        if exams:
            excel_data = []
            for exam in exams:
                seating_data = planner.get_seating_plan(exam['id'])
                for seat in seating_data:
                    start_time = exam['start_time']
                    if hasattr(start_time, 'strftime'):
                        saat = start_time.strftime('%H:%M')
                    else:
                        total_seconds = int(start_time.total_seconds())
                        saat = f"{(total_seconds // 3600) % 24:02d}:{(total_seconds % 3600) // 60:02d}"
                    excel_data.append({
                        'Sınav': f"{exam['course_code']} - {exam['exam_type']}",
                        'Tarih': exam['exam_date'].strftime('%d.%m.%Y'),
                        'Saat': saat,
                        'Derslik': seat['classroom_code'],
                        'Sıra': seat['seat_row'],
                        'Sütun': seat['seat_col'],
                        'Öğrenci No': seat['student_no'],
                        'Ad Soyad': seat['full_name']
                    })
            
            df = pd.DataFrame(excel_data)
            df.to_excel(writer, sheet_name='Oturma Planları', index=False)
    
    def _export_classroom_usage_sheet(self, writer):
        """Derslik kullanımı sayfasını oluşturur."""
        connection = get_db_connection()
        if not connection:
            return
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT cl.code as derslik_kodu, cl.name as derslik_adi, cl.capacity as kapasite,
                       COUNT(DISTINCT e.id) as sinav_sayisi,
                       COUNT(sa.student_id) as toplam_ogrenci,
                       AVG(COUNT(sa.student_id)) OVER (PARTITION BY cl.id) as ortalama_kullanim
                FROM classrooms cl
                LEFT JOIN exam_assignments ea ON cl.id = ea.classroom_id
                LEFT JOIN exams e ON ea.exam_id = e.id
                LEFT JOIN seating_assignments sa ON e.id = sa.exam_id AND cl.id = sa.classroom_id
                WHERE cl.department_id = %s
                GROUP BY cl.id, cl.code, cl.name, cl.capacity
                ORDER BY cl.code
            """
            cursor.execute(query, (self.department_id,))
            data = cursor.fetchall()
            
            if data:
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name='Derslik Kullanımı', index=False)
        except Exception as e:
            print(f"Derslik kullanımı verisi alınırken hata: {e}")
        finally:
            connection.close()
    
    def _export_student_exam_sheet(self, writer):
        """Öğrenci sınav listesi sayfasını oluşturur."""
        connection = get_db_connection()
        if not connection:
            return
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT s.student_no, s.full_name, s.class_level,
                       c.code as ders_kodu, c.name as ders_adi,
                       e.exam_type, e.exam_date, e.start_time,
                       cl.code as derslik, sa.seat_row, sa.seat_col
                FROM students s
                JOIN enrollments en ON s.id = en.student_id
                JOIN courses c ON en.course_id = c.id
                JOIN exams e ON c.id = e.course_id
                JOIN seating_assignments sa ON e.id = sa.exam_id AND s.id = sa.student_id
                JOIN classrooms cl ON sa.classroom_id = cl.id
                WHERE c.department_id = %s
                ORDER BY s.student_no, e.exam_date, e.start_time
            """
            cursor.execute(query, (self.department_id,))
            data = cursor.fetchall()
            
            if data:
                # Tarih formatını düzenle
                for row in data:
                    row['exam_date'] = row['exam_date'].strftime('%d.%m.%Y')
                    st = row['start_time']
                    if hasattr(st, 'strftime'):
                        row['start_time'] = st.strftime('%H:%M')
                    else:
                        total_seconds = int(st.total_seconds())
                        row['start_time'] = f"{(total_seconds // 3600) % 24:02d}:{(total_seconds % 3600) // 60:02d}"
                
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name='Öğrenci Sınav Listesi', index=False)
        except Exception as e:
            print(f"Öğrenci sınav verisi alınırken hata: {e}")
        finally:
            connection.close()
    
    def _get_exam_classrooms(self, exam_id):
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
    
    def generate_pdf_report(self, file_path):
        """PDF raporu oluşturur (basit metin tabanlı)."""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Başlık
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Center
            )
            story.append(Paragraph("Sınav Programı Raporu", title_style))
            story.append(Spacer(1, 20))
            
            # Sınav programı tablosu
            scheduler = ExamScheduler(self.department_id)
            exams = scheduler.get_scheduled_exams()
            
            if exams:
                # Tablo başlıkları
                table_data = [['Tarih', 'Saat', 'Sınav Türü', 'Ders Kodu', 'Ders Adı', 'Sınıf', 'Öğretim Üyesi']]
                
                for exam in exams:
                    st = exam['start_time']
                    if hasattr(st, 'strftime'):
                        saat = st.strftime('%H:%M')
                    else:
                        total_seconds = int(st.total_seconds())
                        saat = f"{(total_seconds // 3600) % 24:02d}:{(total_seconds % 3600) // 60:02d}"
                    table_data.append([
                        exam['exam_date'].strftime('%d.%m.%Y'),
                        saat,
                        exam['exam_type'],
                        exam['course_code'],
                        exam['course_name'],
                        str(exam['class_level']),
                        exam['instructor_name']
                    ])
                
                # Tablo oluştur
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                
                story.append(table)
                story.append(Spacer(1, 20))
            
            # PDF'i oluştur
            doc.build(story)
            
            return True, f"PDF raporu başarıyla oluşturuldu: {file_path}"
            
        except ImportError:
            return False, "PDF oluşturmak için reportlab kütüphanesi gerekli. 'pip install reportlab' komutu ile yükleyin."
        except Exception as e:
            return False, f"PDF oluşturma hatası: {str(e)}"

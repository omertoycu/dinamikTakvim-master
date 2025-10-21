# excel_processor.py
# Excel dosyalarını okuma ve veritabanına aktarma işlemlerini yönetir.

import pandas as pd
import re
from database import (add_instructor, add_course, add_student, add_enrollment, 
                       get_course_by_code, get_student_by_no, get_db_connection)

def process_courses_excel(file_path, department_id):
    """
    Ders listesi Excel dosyasını işler ve veritabanına aktarır.
    Excel formatı: DERS KODU, DERSİN ADI, DERSİ VEREN ÖĞR. ELEMANI
    Aralarda sınıf bilgileri var (örn: "1. Sınıf", "2. Sınıf" vb.)
    """
    try:
        # Excel dosyasını oku
        df = pd.read_excel(file_path)
        
        # Sütun isimlerini standartlaştır
        df.columns = df.columns.str.strip()
        
        # Sütun isimlerini kontrol et ve düzelt
        expected_columns = ['DERS KODU', 'DERSİN ADI', 'DERSİ VEREN ÖĞR. ELEMANI']
        if not all(col in df.columns for col in expected_columns):
            # Alternatif sütun isimlerini dene (esnek eşleşme)
            column_mapping = {}
            for col in df.columns:
                upper_col = str(col).upper().strip()
                if ('DERS' in upper_col and 'KOD' in upper_col) or upper_col in ['KOD', 'KODU', 'DERS KODU']:
                    column_mapping[col] = 'DERS KODU'
                    continue
                if ('DERS' in upper_col and ('AD' in upper_col or 'ADI' in upper_col)) or upper_col in ['DERS ADI', 'DERSİN ADI']:
                    column_mapping[col] = 'DERSİN ADI'
                    continue
                if ('VEREN' in upper_col) or ('ÖĞRETİM' in upper_col) or ('OGRETIM' in upper_col) or ('ELEMAN' in upper_col):
                    column_mapping[col] = 'DERSİ VEREN ÖĞR. ELEMANI'
                    continue
            
            # Sütun isimlerini yeniden adlandır
            if column_mapping:
                df = df.rename(columns=column_mapping)
            
            # Hala gerekli sütunlar yoksa hata ver
            if not all(col in df.columns for col in expected_columns):
                # Header yanlış/hiç olmayabilir: header=None ile tekrar dene ve 3 sütunlu şablon olarak işle
                df_no_header = pd.read_excel(file_path, header=None)
                df_no_header.columns = ['C0', 'C1', 'C2'][: len(df_no_header.columns)]
                # Bu formatta satırların bir kısmı "1. Sınıf" gibi sınıf belirteci, diğerleri [kod, ad, hoca]
                results = {
                    'success': 0,
                    'errors': [],
                    'warnings': []
                }
                current_class_level = None
                for index, row in df_no_header.iterrows():
                    try:
                        val0 = str(row.get('C0', '')).strip()
                        val1 = str(row.get('C1', '')).strip() if 'C1' in df_no_header.columns else ''
                        val2 = str(row.get('C2', '')).strip() if 'C2' in df_no_header.columns else ''

                        if not val0 and not val1 and not val2:
                            continue

                        # Sınıf satırı tespiti
                        if 'sınıf' in val0.lower():
                            class_match = re.search(r'(\d+)', val0)
                            if class_match:
                                current_class_level = int(class_match.group(1))
                            continue

                        course_code = val0
                        course_name = val1
                        instructor_name = val2

                        # Geçersiz değerleri kontrol et ve atla
                        invalid_values = ['nan', 'NaN', 'NAN', 'None', '', ' ']
                        if (course_code in invalid_values or course_name in invalid_values or 
                            instructor_name in invalid_values):
                            continue

                        if not course_code or not course_name or not instructor_name:
                            continue

                        # Başlık veya kategori satırlarını atla
                        skip_keywords = ['DERS KODU', 'SEÇMELİ', 'ZORUNLU', 'SINIF', 'SEMESTR']
                        course_code_upper = course_code.upper()
                        course_name_upper = course_name.upper()
                        
                        should_skip = False
                        for keyword in skip_keywords:
                            if (keyword in course_code_upper and len(course_code) < 10) or \
                               (keyword == course_name_upper) or \
                               ('DERS' in course_code_upper and 'KOD' in course_code_upper):
                                should_skip = True
                                break
                        
                        if should_skip:
                            continue
                        
                        # Çok kısa veya geçersiz ders kodlarını atla (en az 3 karakter olmalı)
                        if len(course_code) < 3 or len(course_name) < 3:
                            continue

                        # Öğretim üyesi ekle/al
                        instructor_id, instructor_msg = add_instructor(instructor_name)
                        if not instructor_id:
                            results['errors'].append(f"Satır {index+1}: {instructor_msg}")
                            continue

                        course_type = "Seçmeli" if "SEÇ" in course_code.upper() else "Zorunlu"
                        # Ders kodundan sınıf seviyesi çıkar (örn: BLM1xx -> 1)
                        code_level_match = re.search(r'(\d)', course_code)
                        level_for_course = int(code_level_match.group(1)) if code_level_match else None
                        effective_level = level_for_course if level_for_course is not None else (current_class_level or 1)

                        course_id, course_msg = add_course(
                            department_id, instructor_id, course_code, course_name, course_type, effective_level
                        )
                        if course_id:
                            # Mevcut dersleri de başarı olarak say
                            results['success'] += 1
                        else:
                            results['errors'].append(f"Satır {index+1}: {course_msg}")
                    except Exception as e:
                        results['errors'].append(f"Satır {index+1}: {str(e)}")

                return results
        
        # Boş satırları agresif temizleme KALDIRILDI, satır içinde kontrol edeceğiz
        
        results = {
            'success': 0,
            'errors': [],
            'warnings': []
        }
        
        current_class_level = None
        
        for index, row in df.iterrows():
            try:
                # Sınıf bilgisi kontrolü
                if pd.isna(row['DERS KODU']) and pd.isna(row['DERSİN ADI']):
                    # Bu satır sınıf bilgisi olabilir
                    instructor_name = str(row['DERSİ VEREN ÖĞR. ELEMANI']).strip()
                    if 'sınıf' in instructor_name.lower():
                        # Sınıf numarasını çıkar (örn: "1. Sınıf" -> 1)
                        class_match = re.search(r'(\d+)', instructor_name)
                        if class_match:
                            current_class_level = int(class_match.group(1))
                    continue
                
                # Ders bilgilerini al (NaN güvenli)
                course_code = str(row.get('DERS KODU', '')).strip() if pd.notna(row.get('DERS KODU', '')) else ''
                course_name = str(row.get('DERSİN ADI', '')).strip() if pd.notna(row.get('DERSİN ADI', '')) else ''
                instructor_name = str(row.get('DERSİ VEREN ÖĞR. ELEMANI', '')).strip() if pd.notna(row.get('DERSİ VEREN ÖĞR. ELEMANI', '')) else ''
                
                # Geçersiz değerleri kontrol et ve atla
                invalid_values = ['nan', 'NaN', 'NAN', 'None', '', ' ']
                if (course_code in invalid_values or course_name in invalid_values or 
                    instructor_name in invalid_values):
                    continue
                
                # Boş değerleri atla
                if not course_code or not course_name or not instructor_name:
                    continue
                
                # Başlık veya kategori satırlarını atla
                skip_keywords = ['DERS KODU', 'SEÇMELİ', 'ZORUNLU', 'SINIF', 'SEMESTR']
                course_code_upper = course_code.upper()
                course_name_upper = course_name.upper()
                
                should_skip = False
                for keyword in skip_keywords:
                    if (keyword in course_code_upper and len(course_code) < 10) or \
                       (keyword == course_name_upper):
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                # Çok kısa veya geçersiz ders kodlarını atla (en az 3 karakter olmalı)
                if len(course_code) < 3 or len(course_name) < 3:
                    continue
                
                # Öğretim üyesini ekle/al
                instructor_id, instructor_msg = add_instructor(instructor_name)
                if not instructor_id:
                    results['errors'].append(f"Satır {index+2}: {instructor_msg}")
                    continue
                
                # Ders tipini belirle (basit kural: kodda "SEÇ" varsa seçmeli)
                course_type = "Seçmeli" if "SEÇ" in course_code.upper() else "Zorunlu"
                
                # Sınıf seviyesi: öncelik ders kodundan, yoksa önceki bloktan
                code_level_match = re.search(r'(\d)', course_code)
                level_for_course = int(code_level_match.group(1)) if code_level_match else None
                effective_level = level_for_course if level_for_course is not None else (current_class_level or 1)
                
                # Dersi ekle
                # Başlık satırı benzeri durumları atla
                if ('DERS' in course_code.upper() and 'KOD' in course_code.upper()) or course_code.upper() in ['DERS KODU', 'KOD', 'KODU']:
                    continue

                course_id, course_msg = add_course(
                    department_id, instructor_id, course_code, 
                    course_name, course_type, effective_level
                )
                
                if course_id:
                    # Mevcut dersleri de başarı olarak say
                    results['success'] += 1
                else:
                    results['errors'].append(f"Satır {index+2}: {course_msg}")
                    
            except Exception as e:
                results['errors'].append(f"Satır {index+2}: {str(e)}")
        
        return results
        
    except Exception as e:
        return {
            'success': 0,
            'errors': [f"Excel dosyası okunamadı: {str(e)}"],
            'warnings': []
        }

def process_students_excel(file_path):
    """
    Öğrenci listesi Excel dosyasını işler ve veritabanına aktarır.
    Excel formatı: Öğrenci No, Ad Soyad, Sınıf, Ders
    """
    try:
        # Excel dosyasını oku (string olarak yükle, tür hatalarını önlemek için)
        df = pd.read_excel(file_path, dtype=str)
        df.columns = df.columns.str.strip()
        
        # Sütun isimlerini kontrol et ve düzelt
        expected_columns = ['Öğrenci No', 'Ad Soyad', 'Sınıf', 'Ders']
        if not all(col in df.columns for col in expected_columns):
            # Alternatif sütun isimlerini dene
            column_mapping = {}
            for col in df.columns:
                if 'ÖĞRENCİ NO' in col.upper() or 'NO' in col.upper():
                    column_mapping[col] = 'Öğrenci No'
                elif 'AD SOYAD' in col.upper() or 'AD' in col.upper():
                    column_mapping[col] = 'Ad Soyad'
                elif 'SINIF' in col.upper():
                    column_mapping[col] = 'Sınıf'
                elif 'DERS' in col.upper():
                    column_mapping[col] = 'Ders'
            
            # Sütun isimlerini yeniden adlandır
            df = df.rename(columns=column_mapping)
            
            # Hala gerekli sütunlar yoksa hata ver
            if not all(col in df.columns for col in expected_columns):
                return {
                    'success': 0,
                    'errors': [f"Gerekli sütunlar bulunamadı. Mevcut sütunlar: {list(df.columns)}"],
                    'warnings': []
                }
        
        # Boş satırları temizle (NaN ve boş stringler)
        df[['Öğrenci No', 'Ad Soyad', 'Sınıf']] = df[['Öğrenci No', 'Ad Soyad', 'Sınıf']].fillna('').applymap(lambda x: x.strip())
        df = df[(df['Öğrenci No'] != '') & (df['Ad Soyad'] != '') & (df['Sınıf'] != '')]
        
        results = {
            'success': 0,
            'errors': [],
            'warnings': [],
            'enrollments': 0
        }
        
        # Performans: Tek bağlantı ile toplu ekleme ve önbellekli eşleme
        connection = get_db_connection()
        if not connection:
            return {
                'success': 0,
                'errors': ["Veritabanı bağlantısı kurulamadı."],
                'warnings': []
            }
        try:
            cursor = connection.cursor()

            # 1) Kurs haritasını önceden yükle (kod veya ad -> id)
            unique_course_codes = sorted({str(x).strip() for x in df['Ders'].fillna('').tolist() if str(x).strip()})
            code_to_id = {}
            name_to_id = {}
            if unique_course_codes:
                # MySQL IN için 1000'lik parçalar
                for i in range(0, len(unique_course_codes), 1000):
                    chunk = unique_course_codes[i:i+1000]
                    placeholders = ','.join(['%s'] * len(chunk))
                    # Koddan eşle
                    cursor.execute(f"SELECT code, id FROM courses WHERE code IN ({placeholders})", tuple(chunk))
                    for code, cid in cursor.fetchall():
                        code_to_id[code] = cid
                    # İsimden eşle
                    cursor.execute(f"SELECT name, id FROM courses WHERE name IN ({placeholders})", tuple(chunk))
                    for name, cid in cursor.fetchall():
                        name_to_id[name] = cid

            # 2) Mevcut öğrencileri toplu kontrol et (no -> id)
            unique_student_nos = sorted({(str(x).strip()) for x in df['Öğrenci No'].fillna('').tolist() if str(x).strip()})
            existing_student_nos = set()
            student_no_to_id = {}
            for i in range(0, len(unique_student_nos), 1000):
                chunk = unique_student_nos[i:i+1000]
                placeholders = ','.join(['%s'] * len(chunk))
                cursor.execute(f"SELECT student_no, id FROM students WHERE student_no IN ({placeholders})", tuple(chunk))
                for sno, sid in cursor.fetchall():
                    existing_student_nos.add(sno)
                    student_no_to_id[sno] = sid

            # 3) Yeni öğrencileri topla ve toplu ekle
            new_students = []  # (student_no, full_name, class_level)
            new_students_seen = set()  # dosya içi tekilleştirme için
            normalized_rows = []  # işlem için normalize edilmiş satırlar
            for idx, row in df.iterrows():
                student_no = (row.get('Öğrenci No') or '').strip()
                full_name = (row.get('Ad Soyad') or '').strip()
                class_level_str = (row.get('Sınıf') or '').strip()
                m = re.search(r'(\d+)', class_level_str)
                class_level = int(m.group(1)) if m else 1
                course_code = ((row.get('Ders') or '').strip()) or None
                if not student_no or not full_name:
                    continue
                normalized_rows.append((idx, student_no, full_name, class_level, course_code))
                if student_no not in existing_student_nos and student_no not in new_students_seen:
                    new_students.append((student_no, full_name, class_level))
                    new_students_seen.add(student_no)

            if new_students:
                # Duplicate riskine karşı INSERT IGNORE kullan
                cursor.executemany(
                    "INSERT IGNORE INTO students (student_no, full_name, class_level) VALUES (%s, %s, %s)",
                    new_students
                )
                connection.commit()
                # Yeni eklenenlerin id'lerini tekrar çek
                for i in range(0, len(unique_student_nos), 1000):
                    chunk = unique_student_nos[i:i+1000]
                    placeholders = ','.join(['%s'] * len(chunk))
                    cursor.execute(f"SELECT student_no, id FROM students WHERE student_no IN ({placeholders})", tuple(chunk))
                    for sno, sid in cursor.fetchall():
                        student_no_to_id[sno] = sid

            # 4) Başarı sayısı: toplam benzersiz öğrenci sayısı
            results['success'] = len(student_no_to_id)

            # 5) Enrollments toplu
            enrollment_pairs = []  # (student_id, course_id)
            for idx, student_no, full_name, class_level, course_code in normalized_rows:
                if course_code and student_no in student_no_to_id:
                    if course_code in code_to_id:
                        enrollment_pairs.append((student_no_to_id[student_no], code_to_id[course_code]))
                    elif course_code in name_to_id:
                        enrollment_pairs.append((student_no_to_id[student_no], name_to_id[course_code]))

            # Mevcut kayıtları çıkar
            unique_enrollments = sorted(set(enrollment_pairs))
            existing_pairs = set()
            for i in range(0, len(unique_enrollments), 1000):
                chunk = unique_enrollments[i:i+1000]
                # Tuple IN ile kontrol
                placeholders = ','.join(['(%s,%s)'] * len(chunk))
                flat = []
                for a, b in chunk:
                    flat.extend([a, b])
                cursor.execute(f"SELECT student_id, course_id FROM enrollments WHERE (student_id, course_id) IN ({placeholders})", tuple(flat))
                for sid, cid in cursor.fetchall():
                    existing_pairs.add((sid, cid))

            new_pairs = [p for p in unique_enrollments if p not in existing_pairs]
            if new_pairs:
                cursor.executemany("INSERT INTO enrollments (student_id, course_id) VALUES (%s, %s)", new_pairs)
                connection.commit()
                results['enrollments'] = len(new_pairs)
            else:
                results['enrollments'] = 0

            # Uyarılar: bulunamayan ders kodları
            missing_courses = sorted({code for code in {r[4] for r in normalized_rows if r[4]} if code not in code_to_id and code not in name_to_id})
            for code in missing_courses[:50]:
                results['warnings'].append(f"Ders '{code}' bulunamadı")
        
            return results
        except Exception as e:
            return {
                'success': 0,
                'errors': [f"Toplu işlem hatası: {str(e)}"],
                'warnings': []
            }
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            connection.close()
        
    except Exception as e:
        return {
            'success': 0,
            'errors': [f"Excel dosyası okunamadı: {str(e)}"],
            'warnings': []
        }

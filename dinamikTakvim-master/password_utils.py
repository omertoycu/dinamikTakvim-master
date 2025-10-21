# password_utils.py
# Şifre hash'leme ve doğrulama işlemlerini yönetir.

import hashlib
import secrets

def hash_password(password):
    """Şifreyi hash'ler ve salt ekler."""
    # Güvenli salt oluştur
    salt = secrets.token_hex(16)
    
    # Şifre + salt'ı hash'le
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    
    # Salt + hash'i birleştir
    return f"{salt}:{password_hash.hex()}"

def verify_password(password, hashed_password):
    """Şifre doğrulaması yapar."""
    try:
        # Salt ve hash'i ayır
        salt, password_hash = hashed_password.split(':')
        
        # Girilen şifreyi aynı salt ile hash'le
        test_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        
        # Hash'leri karşılaştır
        return test_hash.hex() == password_hash
    except (ValueError, AttributeError):
        return False

def is_legacy_password(password, stored_password):
    """Eski düz metin şifreleri kontrol eder (geçiş için)."""
    return password == stored_password

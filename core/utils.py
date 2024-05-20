from datetime import datetime
from django.contrib.auth.models import User

def check_user_has_password(email):
    try:
        user = User.objects.get(email=email)
        if user.password and user.has_usable_password():
            return True
        return False
    except User.DoesNotExist:
        return False
    
def password_validation(password, confirm_password):
    errors = []

    if password != confirm_password:
        errors.append("Passwords does not match.")
        return errors

    if len(password) < 5:
        errors.append("Password must be at least 5 characters")
        
    return errors

def string_to_date(string_date):
    return datetime.strptime(string_date, "%Y-%m-%d")

def date_to_string(date):
    return date.strftime("%Y-%m-%d") if date else ''
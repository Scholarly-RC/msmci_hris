def password_validation(password, confirm_password):
    """
    Validates if the provided passwords match and meet the minimum length requirement.
    """
    errors = []

    if password != confirm_password:
        errors.append("Passwords does not match.")
        return errors

    if len(password) < 5:
        errors.append("Password must be at least 5 characters")

    return errors

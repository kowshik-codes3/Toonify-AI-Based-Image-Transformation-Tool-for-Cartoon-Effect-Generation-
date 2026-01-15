import bcrypt
from database import get_user, add_user

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def hash_security_answer(answer):
    """Hash security answer (case-insensitive)."""
    normalized_answer = answer.lower().strip()
    return bcrypt.hashpw(normalized_answer.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed_password):
    if isinstance(hashed_password, memoryview):
        hashed_password = hashed_password.tobytes()
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def check_security_answer(answer, hashed_answer):
    """Check security answer (case-insensitive)."""
    if isinstance(hashed_answer, memoryview):
        hashed_answer = hashed_answer.tobytes()
    normalized_answer = answer.lower().strip()
    return bcrypt.checkpw(normalized_answer.encode('utf-8'), hashed_answer)

def signup_user(conn, username, email, password, date_of_birth, age, gender, security_question, security_answer):
    from database import check_user_exists, add_user
    if check_user_exists(conn, username, email):
        return False
    hashed_pw = hash_password(password)
    hashed_security_answer = hash_security_answer(security_answer)
    add_user(conn, username, email, hashed_pw, date_of_birth, age, gender, security_question, hashed_security_answer)
    return True

def login_user(conn, email, password):
    user = get_user(conn, email)
    if user:
        return check_password(password, user[3])
    return False

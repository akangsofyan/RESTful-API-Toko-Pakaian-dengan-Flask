# project/token_mail.py

from itsdangerous import URLSafeTimedSerializer


def generate_confirmation_token(email):
    from run import app
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(
        email,
        salt=str.encode(app.config['SECURITY_PASSWORD_SALT'])
    )


def confirm_token(token, expiration=3600):
    from run import app
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email
from flask_mail import Mail
from flask_mail import Message


def send_email(to, subject, template):
    from run import app
    mail = Mail(app)
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=app.config['MAIL_DEFAULT_SENDER']
    )
    mail.send(msg)

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models.db_models import DBEmailSettings

def send_email(subject: str, body: str, settings: DBEmailSettings) -> bool:
    if not settings.sender_email or not settings.receiver_email or not settings.smtp_server:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.sender_email
        msg['To'] = settings.receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        context = ssl.create_default_context()
        if settings.use_ssl:
            # SSL Connection
            with smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port, context=context, timeout=10) as server:
                if settings.username and settings.password:
                    server.login(settings.username, settings.password)
                server.sendmail(settings.sender_email, settings.receiver_email, msg.as_string())
        else:
            # STARTTLS Connection
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=10) as server:
                server.starttls(context=context)
                if settings.username and settings.password:
                    server.login(settings.username, settings.password)
                server.sendmail(settings.sender_email, settings.receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"SMTP send failure: {e}")
        return False

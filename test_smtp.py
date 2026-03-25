import smtplib
from email.mime.text import MIMEText
import traceback

def test():
    try:
        smtp_user = "zenith.sistema.noreply@gmail.com"
        smtp_password = "uayjkguzvcdesvce"
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        target = "stuart_fsi05@hotmail.com"

        msg = MIMEText("Feedback from User: test@test.com\n\nContent:\nteste de envio")
        msg['Subject'] = 'Novo Feedback - Zenith Interface'
        msg['From'] = smtp_user
        msg['To'] = target

        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.set_debuglevel(1)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            print("SUCESSO")
    except Exception as e:
        print("FALHOU")
        traceback.print_exc()

test()

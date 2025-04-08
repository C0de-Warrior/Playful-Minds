import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os  # Use os.environ to load environment variables
from dotenv import load_dotenv
import string
import random

# Load environment variables from the .env file
load_dotenv()

# Now you can access your environment variables
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 465))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

# SMTP Configuration for Gmail
FROM_EMAIL = "noreply@playfulminds.com"  # You can keep this or use your Gmail address

# -------------------- Helper Function to Send Email --------------------
def send_email(to_email, subject, html_content, plain_text_content=None):
    """Send an email with both HTML and plain text content."""
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = FROM_EMAIL
    message["To"] = to_email

    # Create the plain-text and HTML version of your message
    part1 = MIMEText(plain_text_content or "", "plain")
    part2 = MIMEText(html_content, "html")

    # Attach parts into message container. The email client will try to render the last part first.
    message.attach(part1)
    message.attach(part2)

    # Create secure connection with server and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(FROM_EMAIL, to_email, message.as_string())
    return True

# -------------------- Email Templates --------------------
def forgot_password_template(new_password):
    subject = "Playful Minds - Your New Password"
    plain_text = f"Hello,\n\nYour password has been reset. Your new password is:\n{new_password}\n\nPlease log in and change your password immediately.\n\nRegards,\nPlayful Minds Team"
    html_content = f"""
    <html>
    <body>
        <p>Hello,</p>
        <p>Your password has been reset. Your new password is:</p>
        <h2>{new_password}</h2>
        <p>Please log in and change your password immediately.</p>
        <br>
        <p>Regards,<br>Playful Minds Team</p>
    </body>
    </html>
    """
    return subject, plain_text, html_content


def welcome_admin_template(admin_first_name):
    subject = "Welcome to Playful Minds Admin Portal"
    plain_text = f"Hello {admin_first_name},\n\nWelcome to Playful Minds! Your admin account has been successfully created. Enjoy managing the platform.\n\nRegards,\nPlayful Minds Team"
    html_content = f"""
    <html>
      <body>
        <p>Hello {admin_first_name},</p>
        <p>Welcome to <strong>Playful Minds</strong>! Your admin account has been successfully created.</p>
        <p>Enjoy managing the platform and feel free to reach out if you have any questions.</p>
        <br>
        <p>Regards,<br>Playful Minds Team</p>
      </body>
    </html>
    """
    return subject, plain_text, html_content

def player_account_notice_template(player_first_name, admin_first_name):
    subject = "New Player Account Created on Playful Minds"
    plain_text = f"Hello {player_first_name},\n\nAn admin ({admin_first_name}) has created a new player account for you on Playful Minds. Enjoy the games!\n\nRegards,\nPlayful Minds Team"
    html_content = f"""
    <html>
      <body>
        <p>Hello {player_first_name},</p>
        <p>An admin (<strong>{admin_first_name}</strong>) has created a new player account for you on <strong>Playful Minds</strong>.</p>
        <p>Enjoy exploring the games and learning!</p>
        <br>
        <p>Regards,<br>Playful Minds Team</p>
      </body>
    </html>
    """
    return subject, plain_text, html_content

def report_email_template(report_content):
    subject = "Playful Minds - Requested Report"
    plain_text = f"Hello,\n\nPlease find below the requested report:\n\n{report_content}\n\nRegards,\nPlayful Minds Team"
    html_content = f"""
    <html>
      <body>
        <p>Hello,</p>
        <p>Please find below the requested report:</p>
        <div style="border:1px solid #ccc; padding:10px; margin:10px 0;">{report_content}</div>
        <br>
        <p>Regards,<br>Playful Minds Team</p>
      </body>
    </html>
    """
    return subject, plain_text, html_content

# -------------------- Functions to Send Specific Emails --------------------
def send_forgot_password_email(to_email):

    subject, plain_text, html_content = forgot_password_template(new_password)
    return send_email(to_email, subject, html_content, plain_text)

def send_welcome_admin_email(to_email, admin_first_name):
    subject, plain_text, html_content = welcome_admin_template(admin_first_name)
    return send_email(to_email, subject, html_content, plain_text)

def send_player_account_notice_email(to_email, player_first_name, admin_first_name):
    subject, plain_text, html_content = player_account_notice_template(player_first_name, admin_first_name)
    return send_email(to_email, subject, html_content, plain_text)

def send_report_email(to_email, report_content):
    subject, plain_text, html_content = report_email_template(report_content)
    return send_email(to_email, subject, html_content, plain_text)

# -------------------- Example Usage --------------------
if __name__ == "__main__":
    # For testing purposes only
    test_recipient = "godzit@africau.edu"
    # Test sending a forgot password email
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    reset_link = "http://playfulminds.com/reset?token=abc123"
    send_forgot_password_email(test_recipient)
    # Test sending a welcome admin email
    send_welcome_admin_email(test_recipient, "Alice")
    # Test sending a player account notice email
    send_player_account_notice_email(test_recipient, "Bob", "Alice")
    # Test sending a report email
    send_report_email(test_recipient, "This is a sample report content.")

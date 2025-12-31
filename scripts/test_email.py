import os
from dotenv import load_dotenv

from app.email.gmail_sender import send_email

load_dotenv()

send_email(
    to_address=os.environ.get("EMAIL_TO", "jaflemin@gmail.com"),
    subject="BFC Content Radar — Gmail send test",
    body_text="If you received this, your Gmail API + refresh token setup works.",
)

print("✅ Email sent")

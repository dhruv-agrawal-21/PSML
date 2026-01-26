#!/usr/bin/env python
"""
Simple email send test
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("[TEST] Attempting to send email...")
print(f"From: {settings.DEFAULT_FROM_EMAIL}")
print(f"To: gauravchandak235@gmail.com")

try:
    send_mail(
        'Test Email - Requirement Portal',
        'This is a test email to verify SMTP configuration is working.',
        settings.DEFAULT_FROM_EMAIL,
        ['gauravchandak235@gmail.com'],
        fail_silently=False,
    )
    print("[SUCCESS] Email sent successfully!")
    
except Exception as e:
    print(f"[FAILED] Email send failed: {str(e)}")
    print(f"Error type: {type(e).__name__}")

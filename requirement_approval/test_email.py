#!/usr/bin/env python
"""
Simple email test script to diagnose email sending issues
"""
import os
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import smtplib

print("=" * 60)
print("EMAIL CONFIGURATION TEST")
print("=" * 60)

print(f"\n1. EMAIL BACKEND: {settings.EMAIL_BACKEND}")
print(f"2. EMAIL HOST: {settings.EMAIL_HOST}")
print(f"3. EMAIL PORT: {settings.EMAIL_PORT}")
print(f"4. EMAIL USE TLS: {settings.EMAIL_USE_TLS}")
print(f"5. EMAIL HOST USER: {settings.EMAIL_HOST_USER}")
print(f"6. DEFAULT FROM EMAIL: {settings.DEFAULT_FROM_EMAIL}")

print("\n" + "=" * 60)
print("ATTEMPTING TO SEND TEST EMAIL...")
print("=" * 60)

try:
    # Test 1: Simple send_mail function
    print("\n[TEST 1] Using send_mail()...")
    send_mail(
        'Test Email from Requirement Portal',
        'This is a test email to verify email configuration.',
        settings.DEFAULT_FROM_EMAIL,
        ['yadavkrishna2163@gmail.com'],
        fail_silently=False,
    )
    print("✓ send_mail() SUCCESS!")
    
except Exception as e:
    print(f"✗ send_mail() FAILED: {type(e).__name__}")
    print(f"  Error: {str(e)}")

try:
    # Test 2: EmailMessage
    print("\n[TEST 2] Using EmailMessage()...")
    email = EmailMessage(
        subject='Test Email 2 - EmailMessage',
        body='<h1>Test</h1><p>This is a test email using EmailMessage</p>',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['yadavkrishna2163@gmail.com'],
    )
    email.content_subtype = 'html'
    email.send(fail_silently=False)
    print("✓ EmailMessage() SUCCESS!")
    
except Exception as e:
    print(f"✗ EmailMessage() FAILED: {type(e).__name__}")
    print(f"  Error: {str(e)}")

try:
    # Test 3: Direct SMTP connection
    print("\n[TEST 3] Testing direct SMTP connection...")
    server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
    server.starttls()
    print(f"✓ Connected to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    
    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    print(f"✓ Successfully authenticated as {settings.EMAIL_HOST_USER}")
    server.quit()
    
except smtplib.SMTPAuthenticationError as e:
    print(f"✗ SMTP Authentication FAILED")
    print(f"  Error: {str(e)}")
    print(f"  → Check if 'Less Secure App Access' is enabled for the Gmail account")
    print(f"  → Or use an App-Specific Password instead")
    
except Exception as e:
    print(f"✗ SMTP connection FAILED: {type(e).__name__}")
    print(f"  Error: {str(e)}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

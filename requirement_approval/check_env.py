from decouple import config

email_user = config("EMAIL_HOST_USER", default="NOT_FOUND")
email_backend = config("EMAIL_BACKEND", default="NOT_FOUND") 
from_email = config("DEFAULT_FROM_EMAIL", default="NOT_FOUND")

print(f"EMAIL_HOST_USER: {email_user}")
print(f"EMAIL_BACKEND: {email_backend}")
print(f"DEFAULT_FROM_EMAIL: {from_email}")

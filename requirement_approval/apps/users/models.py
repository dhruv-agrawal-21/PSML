from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'Department User'),
        ('head', 'Department Head'),
        ('admin', 'Admin'),
        ('cfo', 'CFO'),
        ('ceo', 'CEO'),
    ]
    
    DEPARTMENT_CHOICES = [
        ('finance', 'Finance'),
        ('marketing', 'Marketing'),
        ('sales', 'Sales'),
        ('technical', 'Technical'),
        ('executive', 'Executive'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES, default='finance')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"
    
    def is_department_user(self):
        return self.role == 'user'
    
    def is_department_head(self):
        return self.role == 'head'
    
    def is_admin_user(self):
        return self.role == 'admin'
    
    def is_cfo_user(self):
        return self.role == 'cfo'
    
    def is_ceo_user(self):
        return self.role == 'ceo'

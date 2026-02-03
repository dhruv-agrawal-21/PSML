from django.db import models
from apps.users.models import CustomUser


class DepartmentChoice(models.Model):
    """Dynamic department choices that can be managed by admins"""
    value = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Department Choice'
        verbose_name_plural = 'Department Choices'
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name


class RequirementTypeChoice(models.Model):
    """Dynamic requirement type choices that can be managed by admins"""
    value = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Requirement Type Choice'
        verbose_name_plural = 'Requirement Type Choices'
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name


class Requirement(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('modification_requested', 'Modification Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    REQUIREMENT_TYPE_CHOICES = [
        ('material', 'Material'),
        ('service', 'Service'),
    ]
    
    requested_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='requirements')
    date = models.DateField(auto_now_add=True)
    department = models.CharField(max_length=20, choices=CustomUser.DEPARTMENT_CHOICES)
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ])
    requirement_type = models.CharField(max_length=20, choices=REQUIREMENT_TYPE_CHOICES, default='material')
    item_description = models.TextField()
    justification = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    next_approver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='pending_approvals')
    modification_description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True)
    estimated_cost = models.DecimalField(max_digits=15, decimal_places=2)
    quotation_deadline = models.DateField()
    quantity = models.IntegerField(blank=True, null=True)
    duration = models.CharField(max_length=100, blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    was_modified = models.BooleanField(default=False, help_text='Tracks if requirement was modified after approval request')
    last_modified_date = models.DateTimeField(null=True, blank=True, help_text='Timestamp of last modification submission')
    attachment = models.FileField(upload_to='requirements/', blank=True, null=True, help_text='Optional document attachment')
    
    class Meta:
        ordering = ['-created_date']
    
    def __str__(self):
        return f"REQ-{self.id} - {self.item_description[:50]}"

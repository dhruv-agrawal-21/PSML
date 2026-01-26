from django.db import models
from apps.users.models import CustomUser
from apps.requirements.models import Requirement


class Approval(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('request_modification', 'Request Modification'),
    ]
    
    APPROVAL_LEVEL_CHOICES = [
        (1, 'Department Head'),
        (2, 'Admin'),
        (3, 'CFO'),
        (4, 'CEO'),
    ]
    
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    approval_level = models.IntegerField(choices=APPROVAL_LEVEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    comments = models.TextField(blank=True, null=True)
    additional_document = models.FileField(upload_to='documents/', blank=True, null=True, help_text='Optional: Upload additional PDF document')
    approved_date = models.DateTimeField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['approval_level']
    
    def __str__(self):
        return f"Approval for REQ-{self.requirement.id} by {self.approver.username}"

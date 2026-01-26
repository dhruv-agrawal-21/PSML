from django.db import models
from apps.users.models import CustomUser
from apps.requirements.models import Requirement


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('uploaded', 'Uploaded'),
        ('modified', 'Modified'),
    ]
    
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"REQ-{self.requirement.id} - {self.action} by {self.user.username}"

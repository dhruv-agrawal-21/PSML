from django.db import models
from apps.requirements.models import Requirement


class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    template_type = models.CharField(max_length=50)
    requirement = models.ForeignKey(Requirement, on_delete=models.SET_NULL, null=True, blank=True)
    sent_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    class Meta:
        ordering = ['-sent_date']
    
    def __str__(self):
        return f"{self.subject} - {self.recipient}"

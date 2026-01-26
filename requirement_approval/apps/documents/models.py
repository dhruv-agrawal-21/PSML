from django.db import models
from apps.users.models import CustomUser
from apps.requirements.models import Requirement
from apps.approvals.models import Approval


class Document(models.Model):
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, related_name='documents')
    approval = models.ForeignKey(Approval, on_delete=models.SET_NULL, null=True, blank=True)
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    uploaded_date = models.DateTimeField(auto_now_add=True)
    document_type = models.CharField(max_length=50, choices=[
        ('original', 'Original'),
        ('signed', 'Signed'),
    ])
    is_signed = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('under_review', 'Under Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    
    class Meta:
        ordering = ['-uploaded_date']
    
    def __str__(self):
        return f"{self.file_name} - {self.document_type}"

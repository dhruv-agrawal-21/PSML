from django import forms
from .models import Approval


class ApprovalActionForm(forms.ModelForm):
    """Form for approving or rejecting a requirement with comments and optional PDF"""
    
    ACTION_CHOICES = [
        ('approved', 'Approve'),
        ('rejected', 'Reject'),
        ('request_modification', 'Request Modification'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        }),
        label='Decision',
        required=True
    )
    
    class Meta:
        model = Approval
        fields = ['comments', 'additional_document']
        widgets = {
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Enter your comments (required)',
                'required': True,
            }),
            'additional_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf',
                'placeholder': 'Upload additional PDF (optional)',
            }),
        }
        labels = {
            'comments': 'Comments',
            'additional_document': 'Additional Document (Optional PDF)',
        }
    
    def clean_comments(self):
        comments = self.cleaned_data.get('comments')
        if not comments or comments.strip() == '':
            raise forms.ValidationError('Comments are required for approval/rejection decision.')
        return comments

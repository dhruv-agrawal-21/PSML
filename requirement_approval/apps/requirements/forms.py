from django import forms
from django.utils import timezone
from .models import Requirement, DepartmentChoice, RequirementTypeChoice


class RequirementForm(forms.ModelForm):
    """Form for creating and editing requirements"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use dynamic choices from database
        self.fields['department'].choices = [
            (choice.value, choice.display_name) 
            for choice in DepartmentChoice.objects.filter(is_active=True)
        ]
        # Use fixed requirement type options for the create UI
        self.fields['requirement_type'].choices = [
            ('general', 'General'),
            ('capex', 'Capex'),
            ('quotation', 'Quotation'),
            ('it_sap', 'IT or SAP'),
            ('advance', 'Advance'),
        ]
    
    class Meta:
        model = Requirement
        fields = [
            'department',
            'priority',
            'requirement_type',
            'item_description',
            'justification',
            'attachment',
        ]
        widgets = {
            'department': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'requirement_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'item_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed description of the required item',
                'required': True,
            }),
            'justification': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Why is this requirement needed? Business justification (Optional)',
                'required': False,
            }),

            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.txt',
                'placeholder': 'Upload supporting document (Optional)',
            }),
        }



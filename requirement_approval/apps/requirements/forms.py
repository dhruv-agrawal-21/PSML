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
        self.fields['requirement_type'].choices = [
            (choice.value, choice.display_name) 
            for choice in RequirementTypeChoice.objects.filter(is_active=True)
        ]
    
    class Meta:
        model = Requirement
        fields = [
            'department',
            'priority',
            'requirement_type',
            'item_description',
            'justification',
            'estimated_cost',
            'quotation_deadline',
            'quantity',
            'duration',
            'delivery_address',
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
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Estimated cost in currency',
                'step': '0.01',
                'min': '0',
                'required': True,
            }),
            'quotation_deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Quantity required (Optional)',
                'min': '1',
                'required': False,
            }),
            'duration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 30 days, 6 months, ongoing (Optional)',
                'required': False,
            }),
            'delivery_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full delivery address (Optional)',
                'required': False,
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.txt',
                'placeholder': 'Upload supporting document (Optional)',
            }),
        }

    def clean_estimated_cost(self):
        cost = self.cleaned_data.get('estimated_cost')
        if cost and cost < 0:
            raise forms.ValidationError('Cost cannot be negative.')
        return cost

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity < 1:
            raise forms.ValidationError('Quantity must be at least 1.')
        return quantity

    def clean_quotation_deadline(self):
        deadline = self.cleaned_data.get('quotation_deadline')
        # Only validate future date if this is a new requirement (no instance) or if deadline is being changed
        if deadline and self.instance.pk:
            # Editing existing requirement - allow any valid date (past dates OK for already-created requirements)
            return deadline
        elif deadline and deadline < timezone.now().date():
            # Creating new requirement - must be future date
            raise forms.ValidationError('Quotation deadline cannot be in the past.')
        return deadline

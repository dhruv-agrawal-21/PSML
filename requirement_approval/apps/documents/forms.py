from django import forms
from .models import Document


class DocumentUploadForm(forms.ModelForm):
    """Form for uploading signed documents during approval process"""
    
    class Meta:
        model = Document
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf,.pdf',
                'required': True,
            }),
        }
        labels = {
            'file': 'Upload Signed PDF Document',
        }
    
    def clean_file(self):
        """Validate uploaded file"""
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file extension
            if not file.name.lower().endswith('.pdf'):
                raise forms.ValidationError('Only PDF files are allowed.')
            
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if file.size > max_size:
                raise forms.ValidationError(f'File size must not exceed 10MB. Current size: {file.size / (1024 * 1024):.2f}MB')
            
            # Check if file is actually a PDF (basic check)
            file.seek(0)
            header = file.read(5)
            file.seek(0)
            if header != b'%PDF-':
                raise forms.ValidationError('Invalid PDF file. The file appears to be corrupted or not a valid PDF.')
        
        return file

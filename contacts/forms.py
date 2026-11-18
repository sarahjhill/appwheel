from django import forms

from .models import PersonalContact


class PersonalContactForm(forms.ModelForm):
    class Meta:
        model = PersonalContact
        fields = ['label', 'name', 'phone', 'email']
        widgets = {
            'phone': forms.TextInput(attrs={'type': 'tel', 'inputmode': 'tel', 'autocomplete': 'off'}),
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('phone') and not cleaned.get('email'):
            raise forms.ValidationError('Please add a phone number or an email address.')
        return cleaned

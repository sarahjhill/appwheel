from django import forms

from .models import DiaryEntry


class DiaryEntryForm(forms.ModelForm):
    class Meta:
        model = DiaryEntry
        fields = [field for field, _ in DiaryEntry.QUESTIONS] + ['rating', 'notes']
        widgets = {
            field: forms.RadioSelect for field, _ in DiaryEntry.QUESTIONS
        } | {
            'rating': forms.RadioSelect,
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'For example: arrived 40 minutes late, rushed, didn\'t help me wash.',
            }),
        }
        labels = dict(DiaryEntry.QUESTIONS) | {'rating': 'How was your care overall?'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Every question can be skipped: drop the empty "---------" choice from the radios
        for name in list(self.fields):
            field = self.fields[name]
            if isinstance(field.widget, forms.RadioSelect):
                field.choices = [(value, label) for value, label in field.choices if value]
                field.required = False


class DownloadForm(forms.Form):
    start = forms.DateField(label='From', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    end = forms.DateField(label='To', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start'), cleaned.get('end')
        if start and end and start > end:
            raise forms.ValidationError('The "From" date needs to be before the "To" date.')
        return cleaned

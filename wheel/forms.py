from django import forms

from .models import Subscription


class DateInput(forms.DateInput):
    """Shows the phone or browser's own date picker."""
    input_type = 'date'

    def __init__(self, **kwargs):
        super().__init__(format='%Y-%m-%d', **kwargs)


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = [
            'common_app', 'name', 'plan_name', 'category', 'price', 'billing_period',
            'next_payment_date', 'trial_end_date', 'usage', 'benefits',
        ]
        widgets = {
            'common_app': forms.HiddenInput(),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
            'next_payment_date': DateInput(),
            'trial_end_date': DateInput(),
        }


class MultipleFileInput(forms.ClearableFileInput):
    """Lets people choose more than one file at once."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if isinstance(data, (list, tuple)):
            return [super(MultipleFileField, self).clean(item, initial) for item in data]
        return [super().clean(data, initial)]


class StatementUploadForm(forms.Form):
    statements = MultipleFileField(
        label='Your bank statements (PDF or CSV)',
        help_text='You can choose up to 6 files at once, for example one for each month.',
        widget=MultipleFileInput(attrs={'accept': '.csv,.pdf,text/csv,application/pdf'}),
    )

    def clean_statements(self):
        statements = self.cleaned_data['statements']
        if len(statements) > 6:
            raise forms.ValidationError('Please choose up to 6 statements at a time.')
        for statement in statements:
            if not statement.name.lower().endswith(('.csv', '.pdf')):
                raise forms.ValidationError(
                    f'{statement.name} isn\'t a PDF or CSV file. Please choose the statement your bank gave you.'
                )
        return statements


class ScreenshotUploadForm(forms.Form):
    screenshots = MultipleFileField(
        label='Your screenshots',
        help_text='PNG or JPG pictures. You can choose up to 5 at once.',
        widget=MultipleFileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}),
    )

    def clean_screenshots(self):
        screenshots = self.cleaned_data['screenshots']
        if len(screenshots) > 5:
            raise forms.ValidationError('Please choose up to 5 screenshots at a time.')
        return screenshots

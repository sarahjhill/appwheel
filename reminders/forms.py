from django import forms

from .models import Reminder

DEFAULT_CHECKLIST = {
    Reminder.Kind.APPOINTMENT: [
        'Appointment letter',
        'List of your medication',
        'Questions you want to ask',
        'Someone to come with you?',
    ],
}


class ReminderForm(forms.ModelForm):
    checklist_text = forms.CharField(
        label='Things to take or do',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text='One per line. Each one becomes a box you can tick.',
    )

    class Meta:
        model = Reminder
        fields = ['kind', 'title', 'due_date', 'time', 'details', 'repeat_every_days']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'time': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'details': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Automatic and cancelling reminders are made by AppWheel, not typed in
        self.fields['kind'].choices = [
            (value, label) for value, label in Reminder.Kind.choices
            if value in (Reminder.Kind.APPOINTMENT, Reminder.Kind.PRESCRIPTION, Reminder.Kind.OTHER)
        ]
        if self.instance.pk:
            self.fields['checklist_text'].initial = '\n'.join(
                item.text for item in self.instance.checklist.all()
            )

    def checklist_lines(self):
        text = self.cleaned_data.get('checklist_text', '')
        return [line.strip() for line in text.splitlines() if line.strip()][:20]

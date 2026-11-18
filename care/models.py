from django.conf import settings
from django.db import models


class CareDiary(models.Model):
    """Records that the user chose to start a care diary (it holds health information)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='care_diary')
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'care diaries'

    def __str__(self):
        return f'Care diary for {self.user}'


class DiaryEntry(models.Model):
    """One day's care: was it on time, kind, and did the person get what they needed?"""

    class Answer(models.TextChoices):
        YES = 'yes', 'Yes'
        NO = 'no', 'No'

    class Rating(models.TextChoices):
        GOOD = 'good', 'Good'
        OK = 'ok', 'OK'
        POOR = 'poor', 'Poor'

    # The questions, in the order they're asked
    QUESTIONS = [
        ('on_time', 'Did your carer arrive on time?'),
        ('kind_and_respectful', 'Were you treated with kindness and respect?'),
        ('medication_given', 'Did you get your medication as planned?'),
        ('personal_care_given', 'Did you get help with food, washing and dressing as agreed?'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='diary_entries')
    date = models.DateField()
    on_time = models.CharField(max_length=3, choices=Answer.choices, blank=True)
    kind_and_respectful = models.CharField(max_length=3, choices=Answer.choices, blank=True)
    medication_given = models.CharField(max_length=3, choices=Answer.choices, blank=True)
    personal_care_given = models.CharField(max_length=3, choices=Answer.choices, blank=True)
    rating = models.CharField('overall', max_length=4, choices=Rating.choices, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'diary entries'
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='one_diary_entry_per_day'),
        ]

    def __str__(self):
        return f'{self.user} – {self.date}'

    @property
    def has_concern(self):
        """True if any answer was No, or the day was rated Poor."""
        answers = [getattr(self, field) for field, _ in self.QUESTIONS]
        return 'no' in answers or self.rating == self.Rating.POOR

    @property
    def answers(self):
        """[(question, answer label)] for showing an entry."""
        return [
            (question, getattr(self, f'get_{field}_display')() or 'Not answered')
            for field, question in self.QUESTIONS
        ]

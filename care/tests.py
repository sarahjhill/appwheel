from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CareDiary, DiaryEntry

TODAY = date.today()


def make_user(name='sam'):
    return get_user_model().objects.create_user(
        username=name, email=f'{name}@example.com', password='a-long-test-password-123'
    )


def good_day(**changes):
    data = {
        'on_time': 'yes', 'kind_and_respectful': 'yes', 'medication_given': 'yes',
        'personal_care_given': 'yes', 'rating': 'good', 'notes': '',
    }
    data.update(changes)
    return data


class StartingTheDiaryTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_logged_out_visitors_are_sent_to_log_in(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('care_today')).status_code, 302)

    def test_people_choose_to_start_the_diary_first(self):
        response = self.client.get(reverse('care_today'))
        self.assertRedirects(response, reverse('care_start'))
        response = self.client.get(reverse('care_start'))
        self.assertContains(response, 'AppWheel never sends it to anyone')

        response = self.client.post(reverse('care_start'))
        self.assertRedirects(response, reverse('care_today'))
        self.assertTrue(CareDiary.objects.filter(user=self.user).exists())


class DiaryEntryTests(TestCase):
    def setUp(self):
        self.user = make_user()
        CareDiary.objects.create(user=self.user)
        self.client.force_login(self.user)

    def test_todays_page_asks_the_four_questions(self):
        response = self.client.get(reverse('care_today'))
        for question in [
            'Did your carer arrive on time?',
            'Were you treated with kindness and respect?',
            'Did you get your medication as planned?',
            'Did you get help with food, washing and dressing as agreed?',
        ]:
            self.assertContains(response, question)
        self.assertNotContains(response, '---------')

    def test_saving_todays_entry(self):
        self.client.post(reverse('care_today'), good_day(notes='Lovely carer today'))
        entry = DiaryEntry.objects.get()
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.date, TODAY)
        self.assertEqual(entry.notes, 'Lovely carer today')
        self.assertFalse(entry.has_concern)

    def test_questions_can_be_left_unanswered(self):
        self.client.post(reverse('care_today'), {'notes': 'Only had time for a note'})
        self.assertEqual(DiaryEntry.objects.get().on_time, '')

    def test_saving_again_changes_the_same_days_entry(self):
        self.client.post(reverse('care_today'), good_day())
        self.client.post(reverse('care_today'), good_day(rating='ok'))
        self.assertEqual(DiaryEntry.objects.count(), 1)
        self.assertEqual(DiaryEntry.objects.get().rating, 'ok')

    def test_a_past_day_can_be_filled_in_but_not_a_future_one(self):
        yesterday = TODAY - timedelta(days=1)
        self.client.post(f"{reverse('care_today')}?date={yesterday.isoformat()}", good_day())
        self.assertEqual(DiaryEntry.objects.get().date, yesterday)
        tomorrow = TODAY + timedelta(days=1)
        response = self.client.get(f"{reverse('care_today')}?date={tomorrow.isoformat()}")
        self.assertEqual(response.context['day'], TODAY)

    def test_any_no_shows_the_not_happy_guidance_with_999(self):
        response = self.client.post(reverse('care_today'), good_day(on_time='no'), follow=True)
        self.assertContains(response, 'Not happy with your care?')
        self.assertContains(response, 'If someone is in danger right now, call 999.')
        self.assertContains(response, 'adult safeguarding')
        self.assertContains(response, 'Care Inspectorate Wales')
        self.assertContains(response, 'AppWheel never sends your diary to anyone')

    def test_a_poor_rating_shows_the_guidance_too(self):
        response = self.client.post(reverse('care_today'), good_day(rating='poor'), follow=True)
        self.assertContains(response, 'If someone is in danger right now, call 999.')

    def test_a_good_day_does_not_show_the_guidance(self):
        response = self.client.post(reverse('care_today'), good_day(), follow=True)
        self.assertNotContains(response, 'If someone is in danger right now')
        self.assertContains(response, 'Where to get help')


class HistoryAndPdfTests(TestCase):
    def setUp(self):
        self.user = make_user()
        CareDiary.objects.create(user=self.user)
        self.client.force_login(self.user)
        for days_ago in range(7):
            DiaryEntry.objects.create(
                user=self.user, date=TODAY - timedelta(days=days_ago), on_time='yes',
                rating='poor' if days_ago == 2 else 'good', notes=f'Day {days_ago}',
            )

    def test_history_lists_entries_newest_first_with_concerns_marked(self):
        response = self.client.get(reverse('care_history'))
        entries = list(response.context['entries'])
        self.assertEqual(entries[0].date, TODAY)
        self.assertContains(response, 'diary-item has-concern', count=1)

    def test_a_week_downloads_as_a_pdf(self):
        response = self.client.get(reverse('care_download'), {
            'start': (TODAY - timedelta(days=6)).isoformat(), 'end': TODAY.isoformat(),
        })
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="care-diary-', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_from_date_must_be_before_to_date(self):
        response = self.client.get(reverse('care_download'), {
            'start': TODAY.isoformat(), 'end': (TODAY - timedelta(days=3)).isoformat(),
        })
        self.assertContains(response, 'needs to be before')

    def test_deleting_one_entry(self):
        entry = DiaryEntry.objects.get(date=TODAY)
        self.client.post(reverse('entry_delete', args=[entry.pk]))
        self.assertEqual(DiaryEntry.objects.count(), 6)

    def test_deleting_the_whole_diary_needs_delete_typed(self):
        self.client.post(reverse('diary_delete'), {'confirm': 'nope'})
        self.assertEqual(DiaryEntry.objects.count(), 7)
        self.client.post(reverse('diary_delete'), {'confirm': 'DELETE'})
        self.assertEqual(DiaryEntry.objects.count(), 0)
        self.assertFalse(CareDiary.objects.exists())

    def test_my_pdf_never_includes_someone_elses_entries(self):
        from unittest import mock
        someone_else = make_user('alex')
        DiaryEntry.objects.create(user=someone_else, date=TODAY, notes='ALEX PRIVATE NOTE')
        with mock.patch('care.views.diary_pdf', return_value=b'%PDF') as make_pdf:
            self.client.get(reverse('care_download'), {'start': TODAY.isoformat(), 'end': TODAY.isoformat()})
        entries = make_pdf.call_args.args[1]
        self.assertEqual([entry.user for entry in entries], [self.user])

    def test_i_cannot_delete_someone_elses_entry(self):
        theirs = DiaryEntry.objects.create(user=make_user('alex'), date=TODAY)
        self.assertEqual(self.client.post(reverse('entry_delete', args=[theirs.pk])).status_code, 404)
        self.assertTrue(DiaryEntry.objects.filter(pk=theirs.pk).exists())

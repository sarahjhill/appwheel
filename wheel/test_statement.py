from datetime import date
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Subscription
from .statement import StatementError, find_regular_payments, read_statement

# Like Monzo and Starling: one Amount column, money out is negative
SIMPLE_CSV = """Date,Name,Amount
01/09/2026,NETFLIX.COM,-12.99
01/10/2026,NETFLIX.COM,-12.99
01/11/2026,NETFLIX.COM,-12.99
05/09/2026,PUREGYM LTD,-24.99
05/10/2026,PUREGYM LTD,-24.99
05/11/2026,PUREGYM LTD,-24.99
10/09/2026,Cardiff Council Tax,-150.00
10/10/2026,Cardiff Council Tax,-150.00
10/11/2026,Cardiff Council Tax,-150.00
12/09/2026,TESCO STORES,-45.20
19/09/2026,TESCO STORES,-82.10
26/09/2026,TESCO STORES,-23.50
03/10/2026,TESCO STORES,-60.00
15/10/2026,Spotify P1234ABC,-11.99
20/10/2026,Coffee shop,-3.50
25/10/2026,Salary,2000.00
"""

# Like Nationwide: account details first, then Paid out / Paid in columns
PAID_OUT_CSV = """"Account Name:","FlexAccount ****1234"
"Account Balance:","£500.00"

"Date","Transaction type","Description","Paid out","Paid in","Balance"
"01 Sep 2026","Direct debit","DISNEY PLUS","£4.99","","£495.01"
"01 Oct 2026","Direct debit","DISNEY PLUS","£4.99","","£490.02"
"02 Oct 2026","Bank credit","WAGES","","£1,200.00","£1,690.02"
"""


SAMPLE_PDF = Path(__file__).parent / 'test_files' / 'sample-statement.pdf'


def upload_pdf():
    return SimpleUploadedFile('statement.pdf', SAMPLE_PDF.read_bytes(), content_type='application/pdf')


def upload(text, name='statement.csv'):
    return SimpleUploadedFile(name, text.encode('utf-8'), content_type='text/csv')


class ReadStatementTests(TestCase):
    def test_reads_money_out_and_skips_money_in(self):
        transactions = read_statement(upload(SIMPLE_CSV))
        self.assertEqual(len(transactions), 15)  # the salary is skipped
        self.assertEqual(transactions[0].date, date(2026, 9, 1))
        self.assertEqual(transactions[0].amount, Decimal('12.99'))

    def test_reads_paid_out_columns_and_skips_account_details(self):
        transactions = read_statement(upload(PAID_OUT_CSV))
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0].amount, Decimal('4.99'))

    def test_reads_a_pdf_statement(self):
        transactions = read_statement(upload_pdf())
        # 5 payments out; the wages coming in are skipped
        self.assertEqual(len(transactions), 5)
        self.assertEqual(transactions[0].date, date(2026, 9, 1))
        self.assertEqual(transactions[0].description, 'NETFLIX.COM')
        self.assertEqual(transactions[0].amount, Decimal('12.99'))

    def test_finds_apps_in_a_pdf_statement(self):
        found = {item['name']: item for item in find_regular_payments(read_statement(upload_pdf()))}
        self.assertEqual(found['Netflix']['times_paid'], 3)
        self.assertEqual(found['Sky']['price'], '35.00')
        self.assertNotIn('Corner Shop', found)

    def test_takeaways_that_change_price_are_not_subscriptions(self):
        csv_text = "Date,Name,Amount\n" + "\n".join(
            f"{day:02d}/{month:02d}/2026,DELIVEROO,-{price}"
            for day, month, price in [(1, 9, '23.10'), (1, 10, '12.40'), (1, 11, '31.75')]
        )
        found = find_regular_payments(read_statement(upload(csv_text)))
        self.assertEqual(found, [])

    def test_a_file_without_the_right_columns_gives_a_clear_error(self):
        with self.assertRaises(StatementError):
            read_statement(upload('hello,world\n1,2\n'))


class FindRegularPaymentsTests(TestCase):
    def setUp(self):
        found = find_regular_payments(read_statement(upload(SIMPLE_CSV)))
        self.found = {item['name']: item for item in found}

    def test_finds_monthly_apps(self):
        self.assertEqual(self.found['Netflix']['price'], '12.99')
        self.assertEqual(self.found['Netflix']['billing_period'], 'monthly')
        self.assertEqual(self.found['PureGym']['category'], 'fitness')

    def test_known_apps_count_even_if_paid_once(self):
        self.assertIn('Spotify', self.found)

    def test_regular_bills_are_found_but_not_marked_as_known(self):
        council_tax = [item for item in self.found.values() if 'Council' in item['name']]
        self.assertEqual(len(council_tax), 1)
        self.assertFalse(council_tax[0]['known'])

    def test_food_shops_and_one_off_payments_are_ignored(self):
        names = ' '.join(self.found).lower()
        self.assertNotIn('tesco', names)
        self.assertNotIn('coffee', names)


class StatementPagesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(self.user)

    def test_logged_out_visitors_are_sent_to_log_in(self):
        self.client.logout()
        response = self.client.get(reverse('statement_upload'))
        self.assertEqual(response.status_code, 302)

    def test_only_pdf_and_csv_files_are_accepted(self):
        response = self.client.post(
            reverse('statement_upload'), {'statements': upload('x', name='statement.docx')}
        )
        self.assertContains(response, 'isn&#x27;t a PDF or CSV file')

    def test_a_broken_pdf_gives_a_clear_error(self):
        response = self.client.post(
            reverse('statement_upload'), {'statements': upload('not really a pdf', name='statement.pdf')}
        )
        self.assertContains(response, 'couldn&#x27;t open that PDF')

    def test_several_statements_can_be_uploaded_at_once(self):
        response = self.client.post(
            reverse('statement_upload'), {'statements': [upload(SIMPLE_CSV), upload_pdf()]}
        )
        self.assertRedirects(response, reverse('statement_review'))
        names = [item['name'] for item in self.client.session['statement_found']]
        self.assertIn('PureGym', names)
        self.assertIn('Sky', names)

    def test_upload_then_add_only_the_ticked_apps(self):
        response = self.client.post(reverse('statement_upload'), {'statements': upload(SIMPLE_CSV)})
        self.assertRedirects(response, reverse('statement_review'))

        response = self.client.get(reverse('statement_review'))
        self.assertContains(response, 'Netflix')
        found = self.client.session['statement_found']
        netflix = next(i for i, item in enumerate(found) if item['name'] == 'Netflix')

        response = self.client.post(reverse('statement_review'), {'add': [str(netflix)]})
        self.assertRedirects(response, reverse('subscription_list'))
        subscription = Subscription.objects.get()
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.name, 'Netflix')
        self.assertEqual(subscription.price, Decimal('12.99'))
        self.assertNotIn('statement_found', self.client.session)

    def test_apps_i_already_have_are_not_added_twice(self):
        Subscription.objects.create(user=self.user, name='Netflix', price=Decimal('12.99'))
        self.client.post(reverse('statement_upload'), {'statements': upload(SIMPLE_CSV)})
        found = self.client.session['statement_found']
        everything = [str(i) for i in range(len(found))]
        self.client.post(reverse('statement_review'), {'add': everything})
        self.assertEqual(Subscription.objects.filter(name='Netflix').count(), 1)

    def test_nothing_from_the_statement_is_saved_until_i_tick(self):
        self.client.post(reverse('statement_upload'), {'statements': upload(SIMPLE_CSV)})
        self.assertEqual(Subscription.objects.count(), 0)

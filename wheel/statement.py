"""
Reads a bank statement (CSV file) and finds the payments that repeat,
such as Netflix every month or a gym every week.

The file is read in memory and never saved. Only the payments the user
ticks on the next page are stored, as Subscriptions.
"""
import csv
import io
import re
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation


class StatementError(Exception):
    """Something about the file means we can't read it."""


@dataclass
class Transaction:
    date: date
    description: str
    amount: Decimal  # money out is a positive number


# Well-known apps and subscriptions: words to look for -> (name, category)
KNOWN_APPS = [
    ('netflix', 'Netflix', 'video'),
    ('disney', 'Disney+', 'video'),
    ('now tv', 'NOW', 'video'),
    ('nowtv', 'NOW', 'video'),
    ('prime video', 'Amazon Prime Video', 'video'),
    ('amazon prime', 'Amazon Prime', 'video'),
    ('amznprime', 'Amazon Prime', 'video'),
    ('paramount', 'Paramount+', 'video'),
    ('apple tv', 'Apple TV+', 'video'),
    ('youtube', 'YouTube Premium', 'video'),
    ('britbox', 'BritBox', 'video'),
    ('discovery', 'discovery+', 'video'),
    ('spotify', 'Spotify', 'music'),
    ('apple music', 'Apple Music', 'music'),
    ('tidal', 'Tidal', 'music'),
    ('deezer', 'Deezer', 'music'),
    ('audible', 'Audible', 'books'),
    ('kindle', 'Kindle Unlimited', 'books'),
    ('everand', 'Everand', 'books'),
    ('scribd', 'Everand', 'books'),
    ('icloud', 'iCloud+', 'storage'),
    ('google one', 'Google One', 'storage'),
    ('dropbox', 'Dropbox', 'storage'),
    ('microsoft', 'Microsoft 365', 'storage'),
    ('openai', 'ChatGPT', 'ai'),
    ('chatgpt', 'ChatGPT', 'ai'),
    ('anthropic', 'Claude', 'ai'),
    ('claude.ai', 'Claude', 'ai'),
    ('midjourney', 'Midjourney', 'ai'),
    ('canva', 'Canva', 'design'),
    ('adobe', 'Adobe', 'design'),
    ('figma', 'Figma', 'design'),
    ('puregym', 'PureGym', 'fitness'),
    ('pure gym', 'PureGym', 'fitness'),
    ('the gym', 'The Gym Group', 'fitness'),
    ('david lloyd', 'David Lloyd', 'fitness'),
    ('strava', 'Strava', 'fitness'),
    ('peloton', 'Peloton', 'fitness'),
    ('headspace', 'Headspace', 'fitness'),
    ('calm.com', 'Calm', 'fitness'),
    ('duolingo', 'Duolingo', 'other'),
    ('xbox', 'Xbox Game Pass', 'other'),
    ('playstation', 'PlayStation Plus', 'other'),
    ('nintendo', 'Nintendo Switch Online', 'other'),
    ('deliveroo plus', 'Deliveroo Plus', 'other'),
    ('sky', 'Sky', 'video'),
    ('virgin media', 'Virgin Media', 'other'),
    ('tv licence', 'TV Licence', 'video'),
    ('tvl', 'TV Licence', 'video'),
    ('vodafone', 'Vodafone', 'other'),
    ('giffgaff', 'giffgaff', 'other'),
    ('o2', 'O2', 'other'),
    ('ee limited', 'EE', 'other'),
    ('bt group', 'BT', 'other'),
    ('plusnet', 'Plusnet', 'other'),
    ('talktalk', 'TalkTalk', 'other'),
    ('uber one', 'Uber One', 'other'),
    ('patreon', 'Patreon', 'other'),
    ('linkedin', 'LinkedIn Premium', 'other'),
]

# Column names that banks use (all compared in lower case)
DATE_COLUMNS = ['date', 'transaction date', 'posted date', 'posting date', 'completed date', 'value date']
DESCRIPTION_COLUMNS = [
    'description', 'transaction description', 'name', 'merchant', 'payee',
    'memo', 'details', 'narrative', 'reference', 'counter party',
]
AMOUNT_COLUMNS = ['amount', 'value', 'amount (gbp)', 'transaction amount']
MONEY_OUT_COLUMNS = ['paid out', 'money out', 'debit', 'debit amount', 'out', 'withdrawals']

DATE_FORMATS = [
    '%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y', '%d %b %Y', '%d %B %Y',
    '%d %b %y', '%d-%b-%Y', '%d-%b-%y', '%d.%m.%Y',
]

# Words banks add that aren't part of the shop's name
NOISE_WORDS = re.compile(
    r'\b(card payment to|card payment|payment to|direct debit|dd|d/d|so|s/o|standing order|'
    r'bill payment|debit card|contactless|visa|vis|pos|purchase|recurring|subscription|'
    r'ltd|limited|inc|gbp|uk|gb|london|dublin|luxembourg|www|com|co|help|bill|payment)\b'
)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def read_statement(uploaded_file):
    """Turn an uploaded CSV or PDF statement into a list of money-out Transactions."""
    if uploaded_file.size > MAX_FILE_SIZE:
        raise StatementError('That file is too big. Please choose a statement under 5 MB.')
    if uploaded_file.name.lower().endswith('.pdf'):
        return read_pdf_statement(uploaded_file)
    return read_csv_statement(uploaded_file)


def read_csv_statement(uploaded_file):
    """Read a CSV statement."""
    raw = uploaded_file.read()
    for encoding in ('utf-8-sig', 'cp1252'):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise StatementError("We couldn't read that file. Please download it again as a CSV.")

    rows = [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]
    header_index, columns = _find_header(rows)

    transactions = []
    for row in rows[header_index + 1:]:
        transaction = _read_row(row, columns)
        if transaction:
            transactions.append(transaction)

    if not transactions:
        raise StatementError("We couldn't find any payments in that file.")
    return transactions


# PDF statements -----------------------------------------------------------

PDF_MONEY_IN = ['money in', 'paid in', 'credit', 'credits', 'in']
PDF_MONEY_OUT = ['money out', 'paid out', 'debit', 'debits', 'out', 'withdrawn', 'payments']
MONEY_PATTERN = re.compile(r'^-?£?[\d,]+\.\d{2}(CR|DR)?$')
DATE_START = re.compile(
    r'^(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2} [A-Za-z]{3,9} \d{2,4})'
)


def read_pdf_statement(uploaded_file):
    """
    Read a PDF statement. We find the "Money in" and "Money out" headings,
    then read each line that has an amount underneath them.
    """
    import pdfplumber  # only needed for PDFs

    try:
        pdf = pdfplumber.open(uploaded_file)
    except Exception:
        raise StatementError("We couldn't open that PDF. Please download it again from your bank.")

    transactions = []
    with pdf:
        columns = None
        for page in pdf.pages:
            # Some banks hide tiny labels inside each row for screen readers. Skip them.
            visible = page.filter(
                lambda obj: obj.get('object_type') != 'char' or obj.get('size', 0) >= 3
            )
            lines = _pdf_lines(visible.extract_words(keep_blank_chars=False))
            columns = _pdf_columns(lines) or columns
            if columns:
                transactions.extend(_pdf_transactions(lines, columns))

    if columns is None:
        raise StatementError(
            "We couldn't find the Money in and Money out columns in that PDF. "
            'Try downloading a CSV instead, or tell us which bank it is from.'
        )
    if not transactions:
        raise StatementError("We couldn't find any payments in that PDF.")
    return transactions


def _pdf_lines(words):
    """Group words that sit on the same line, left to right."""
    lines = []
    for word in sorted(words, key=lambda word: (round(word['top']), word['x0'])):
        if lines and abs(lines[-1][0]['top'] - word['top']) < 3:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda word: word['x0']) for line in lines]


def _pdf_columns(lines):
    """Find where the Money in, Money out and Balance columns are on the page."""
    for line in lines:
        text = ' '.join(word['text'] for word in line).lower()
        if 'date' not in text or 'balance' not in text:
            continue
        columns = {}
        for index, word in enumerate(line):
            here = word['text'].lower().strip('(£):')
            pair = (here + ' ' + line[index + 1]['text'].lower().strip('(£):')) if index + 1 < len(line) else ''
            if pair in PDF_MONEY_IN or (here in PDF_MONEY_IN and here != 'in'):
                columns['in'] = _column_right_edge(line, index)
            elif pair in PDF_MONEY_OUT or (here in PDF_MONEY_OUT and here != 'out'):
                columns['out'] = _column_right_edge(line, index)
            elif here == 'balance':
                columns['balance'] = _column_right_edge(line, index)
            elif here == 'type':
                columns['text_end'] = word['x0']
        if 'out' in columns:
            return columns
    return None


def _column_right_edge(line, index):
    """Amounts line up on the right, under the end of the heading."""
    edge = line[index]['x1']
    for word in line[index + 1:index + 3]:
        if word['text'].lower().strip('(£):') in ('in', 'out', '') or word['text'] == '(£)':
            edge = word['x1']
    return edge


def _pdf_transactions(lines, columns):
    transactions = []
    current_date = None
    for line in lines:
        text = ' '.join(word['text'] for word in line)
        match = DATE_START.match(text)
        rest = line
        if match:
            try:
                current_date = _parse_date(match.group(1))
            except ValueError:
                continue
            date_words = len(match.group(1).split())
            rest = line[date_words:]
        if current_date is None:
            continue

        amounts = [word for word in rest if MONEY_PATTERN.match(word['text'])]
        if not amounts:
            continue
        description_words = [
            word['text'] for word in rest
            if word['x1'] < amounts[0]['x0']
            and (not columns.get('text_end') or word['x0'] < columns['text_end'] - 2)
        ]
        description = ' '.join(description_words).strip()
        if not description:
            continue

        for word in amounts:
            column = min(
                (name for name in ('in', 'out', 'balance') if name in columns),
                key=lambda name: abs(columns[name] - word['x1']),
            )
            if column == 'out':
                amount = abs(_parse_money(word['text'].rstrip('CRD')))
                if amount:
                    transactions.append(Transaction(current_date, description, amount))
                break
            if column == 'in':
                break
    return transactions


def _find_header(rows):
    """Find the row with the column names. Some banks put account details above it."""
    for index, row in enumerate(rows[:15]):
        names = [cell.strip().lower() for cell in row]
        columns = {
            'date': _first_match(names, DATE_COLUMNS),
            'description': _first_match(names, DESCRIPTION_COLUMNS),
            'amount': _first_match(names, AMOUNT_COLUMNS),
            'money_out': _first_match(names, MONEY_OUT_COLUMNS),
        }
        if columns['date'] is not None and columns['description'] is not None and (
            columns['amount'] is not None or columns['money_out'] is not None
        ):
            return index, columns
    raise StatementError(
        "We couldn't find the date, description and amount columns. "
        'Please check you downloaded a CSV statement from your banking app.'
    )


def _first_match(names, options):
    for option in options:
        if option in names:
            return names.index(option)
    return None


def _read_row(row, columns):
    try:
        when = _parse_date(row[columns['date']])
        description = row[columns['description']].strip()
        if columns['money_out'] is not None and row[columns['money_out']].strip():
            amount = abs(_parse_money(row[columns['money_out']]))
        elif columns['amount'] is not None:
            amount = _parse_money(row[columns['amount']])
            if amount >= 0:
                return None  # money coming in, not a payment
            amount = -amount
        else:
            return None
    except (IndexError, ValueError, InvalidOperation):
        return None
    if not description or amount == 0:
        return None
    return Transaction(date=when, description=description, amount=amount)


def _parse_date(value):
    value = value.strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    # Some banks add a time, for example "2026-11-01 09:30:00"
    return datetime.strptime(value[:10], '%Y-%m-%d').date()


def _parse_money(value):
    cleaned = value.strip().replace('£', '').replace(',', '').replace(' ', '')
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    return Decimal(cleaned)


def known_app(description):
    """Return (name, category) if the description is a well-known app."""
    lowered = description.lower()
    for words, name, category in KNOWN_APPS:
        if re.search(r'(?<![a-z0-9])' + re.escape(words) + r'(?![a-z0-9])', lowered):
            return name, category
    return None


def _group_key(description):
    """Make 'NETFLIX.COM 12345 GB' and 'Netflix.com 98765' look the same."""
    known = known_app(description)
    if known:
        return known[0].lower()
    lowered = description.lower()
    lowered = re.sub(r'[^a-z ]', ' ', lowered)
    lowered = NOISE_WORDS.sub(' ', lowered)
    words = [word for word in lowered.split() if len(word) > 1]
    return ' '.join(words[:3])


def _tidy_name(description):
    words = re.sub(r'[^A-Za-z&+ ]', ' ', description)
    words = NOISE_WORDS.sub(' ', words.lower()).split()
    # Short names like "EE" or "BT" stay in capitals
    words = [word.upper() if len(word) <= 2 else word.capitalize() for word in words[:3]]
    return ' '.join(words) or description[:40]


def _billing_period(dates):
    """Work out how often a payment happens from the gaps between dates."""
    if len(dates) < 2:
        return None
    gaps = [(later - earlier).days for earlier, later in zip(dates, dates[1:])]
    typical_gap = statistics.median(gaps)
    if 5 <= typical_gap <= 9:
        return 'weekly'
    if 25 <= typical_gap <= 35:
        return 'monthly'
    if 350 <= typical_gap <= 380:
        return 'yearly'
    return None


def find_regular_payments(transactions):
    """
    Group the payments by who they went to, and keep the ones that repeat
    (or that are a well-known app, even if they only appear once).
    """
    groups = {}
    for transaction in transactions:
        groups.setdefault(_group_key(transaction.description), []).append(transaction)

    # One company can take more than one payment, like Sky TV and Sky Broadband.
    # Split each group into payments of a similar amount.
    clusters = []
    for key, payments in groups.items():
        if not key:
            continue
        current = []
        for payment in sorted(payments, key=lambda payment: payment.amount):
            if current and payment.amount > current[0].amount * Decimal('1.25'):
                clusters.append((key, current))
                current = []
            current.append(payment)
        clusters.append((key, current))
    shared_keys = {key for key, _ in clusters if [k for k, _ in clusters].count(key) > 1}

    found = []
    for key, payments in clusters:
        payments.sort(key=lambda payment: payment.date)
        dates = [payment.date for payment in payments]
        latest = payments[-1]
        known = known_app(latest.description)
        period = _billing_period(dates)

        if period is None and not known:
            continue  # a one-off shop, not a subscription
        if period is None:
            period = 'monthly'  # well-known apps are usually monthly

        # Ignore regular payments where the amount jumps around a lot (like food shops)

        step = {'weekly': 7, 'monthly': 30, 'yearly': 365}[period]
        next_payment = latest.date + timedelta(days=step)
        while next_payment < date.today():
            next_payment += timedelta(days=step)

        name, category = known if known else (_tidy_name(latest.description), 'other')
        if key in shared_keys:
            name = _tidy_name(latest.description)  # "Sky TV" and "Sky", not "Sky" twice
        found.append({
            'name': name,
            'category': category,
            'price': str(latest.amount),
            'billing_period': period,
            'last_paid': latest.date.isoformat(),
            'next_payment_date': next_payment.isoformat(),
            'times_paid': len(payments),
            'known': bool(known),
        })

    found.sort(key=lambda item: (not item['known'], item['name'].lower()))
    return found

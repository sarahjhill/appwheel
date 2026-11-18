"""UK emergency and support numbers shown on the Help page (tap to call)."""

EMERGENCY = [
    {
        'name': 'Emergency services',
        'number': '999',
        'link': 'tel:999',
        'when': 'Someone is in danger, badly hurt or seriously ill, or a crime is happening now.',
        'urgent': True,
    },
]

NON_EMERGENCY = [
    {
        'name': 'NHS 111',
        'number': '111',
        'link': 'tel:111',
        'when': 'Medical help or advice that isn\'t an emergency, day or night.',
    },
    {
        'name': 'Police (non-emergency)',
        'number': '101',
        'link': 'tel:101',
        'when': 'To report a crime or get police advice when it isn\'t an emergency.',
    },
    {
        'name': 'Samaritans',
        'number': '116 123',
        'link': 'tel:116123',
        'when': 'Free, any time, if you\'re struggling or need someone to talk to.',
    },
]

CANT_SPEAK = [
    'In an emergency on a mobile, if you can\'t speak: call 999, then press 55 when asked.',
    'Deaf or hard of hearing? Register for emergency texts by texting "register" to 999. '
    'Do this before you need it.',
]

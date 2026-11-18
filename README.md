# AppWheel

**Spin your apps and life into control.**

AppWheel shows every app and subscription you pay for on one spinning wheel. Each app gets a traffic-light health score, so you can see at a glance what's good value, what could cost less and what needs action. Alongside that it keeps your reminders, appointments, a care diary and important contacts in one calm place.

## Features (planned for version 1)

- **The App Wheel** – spin through your apps, see what each one costs a month and a year
- **Traffic-light health scores** – green (good value), amber (could cost less), red (needs action), always shown with a symbol as well as a colour
- **Ways to save** – specific suggestions with £ amounts, such as cheaper plans, duplicate apps and free trials ending
- **Cancel with help** – the right cancel page, simple steps and a reminder to check you weren't charged
- **Reminders** – trials, renewals, appointments with "what to bring" checklists, repeat prescriptions
- **Care diary** – log the care you receive each day, and find out who to send it to if something goes wrong
- **Help and contacts** – emergency and important numbers, one tap away

## Accessibility

AppWheel is built for people who are often overlooked, so it aims to meet **WCAG 2.2 AA**.

Checked in November 2026 (issue #28):

- **Automated check** with axe-core on all 26 pages at phone size: no problems found
- **Keyboard:** every control can be reached with Tab and shows a clear focus outline; the wheel turns with the left and right arrow keys; app cards open as dialogs, close with Escape and return focus to where you were
- **Screen readers:** every app on the wheel is a real button with a full label (for example "Netflix, £12.99 a month, good value"); the selected app is announced; headings are in order on every page
- **Colour:** text meets contrast requirements, and the traffic lights always show a symbol (✓ ! ✕) as well as a colour
- **Zoom and small screens:** nothing scrolls sideways at 320px wide (the same as 400% zoom on a laptop)
- **Tap targets:** buttons and links are at least 24 by 24 pixels, most are 44 or more
- **Motion:** the wheel doesn't spin for people who turn on "reduce motion" on their device

Still to do with real people: testing with VoiceOver (iPhone) and TalkBack (Android), and with disabled testers.

## Tech stack

- Python and Django
- PostgreSQL
- HTML, CSS and JavaScript
- Hosted on Heroku

## Running it locally

1. Clone the repo and open the folder.
2. Create and switch on a virtual environment:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install the packages:
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and add your own `SECRET_KEY`.
5. Start the server:
   ```
   python manage.py runserver
   ```
6. Open http://127.0.0.1:8000

## Status

In development.

## Author

Built by [Sarah J Hill](https://sarahjhill.com).

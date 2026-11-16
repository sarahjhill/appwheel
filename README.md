# AppWheel

**Spins all your apps into control.**

AppWheel shows every app and subscription you pay for on one spinning wheel. Each app gets a traffic-light health score, so you can see at a glance what's good value, what could cost less and what needs action. Alongside that it keeps your reminders, appointments, a care diary and important contacts in one calm place.

## Features (planned for version 1)

- **The App Wheel** – spin through your apps, see what each one costs a month and a year
- **Traffic-light health scores** – green (good value), amber (could cost less), red (needs action), always shown with a symbol as well as a colour
- **Ways to save** – specific suggestions with £ amounts, such as cheaper plans, duplicate apps and free trials ending
- **Cancel with help** – the right cancel page, simple steps and a reminder to check you weren't charged
- **Reminders** – trials, renewals, appointments with "what to bring" checklists, repeat prescriptions
- **Care diary** – log the care you receive each day, and find out who to send it to if something goes wrong
- **Help and contacts** – emergency and important numbers, one tap away

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

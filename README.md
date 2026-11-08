# Vijetha Academy V10 – Master Admin Panel (Flask)

## Run
    pip install -r requirements.txt
    python app.py            # http://127.0.0.1:5000   (admin panel: /admin)

Default Super Admin: **admin / 1**. The panel shows a warning until you change it (My profile).
For production: serve behind HTTPS, set `HTTPS=1` and `SECRET_KEY`, and run with gunicorn (`gunicorn app:app`).

## Environment variables
- `DATABASE_URL` – `sqlite:///…` (default), `postgresql://user:pw@host/db`, `mysql://user:pw@host/db` (needs PyMySQL / psycopg2)
- `VIJETHA_DATA` – folder for database, uploads, secret key (default `./instance`)
- `SMTP_HOST/PORT/USER/PASS/FROM` – enables recovery emails; otherwise reset links go to `instance/recovery.log`

## Layout
- `schema.py` – every module (fields, validation, UI columns, default roles). API and admin UI are generated from it.
- `core.py` – DB layer, HTML/SVG sanitisers, auth, permissions. `admin_api.py` – REST API. `public.py` – public site + student area.
- `templates/`, `static/` – public templates and the admin SPA (`admin.js`).

## Honest limits
- Content is stored in one portable `records` table (JSON per row) so SQLite/MySQL/PostgreSQL share a schema. Only SQLite was run in testing.
- Payments use a **manual** provider (student submits a reference; admin marks paid or records a refund). No Razorpay/Stripe call exists yet.
- Settings are versioned and restorable; posts, pages, courses and notices keep per-record history. Drafts can be previewed with `?preview=1` while logged in.
- Only the Super Admin can edit role permissions.

## Public website redesign (blue / white / gold)
Only these public-site files changed: `templates/base.html`, `templates/home.html`, `templates/_icons.html` (new), `static/site.css`, `static/site.js`.
The admin panel, backend, API, database and admin routes are unchanged (`/admin` is the existing login).

Where the new homepage reads its content (all managed from the existing admin panel):
- **Gallery slider** – Sliders, Promo banners, and posts in category `Gallery`.
- **Academy videos** – any published post that has a Video link (YouTube or .mp4).
- **Our Pride** – published posts in category `Our Pride`: title = student name, short description = `Exam name | Marks`, cover image = photo, first tag = academic year.
- **Admission form** – saved through the existing contact endpoint, so applications appear in Admin → Enquiries as `ADMISSION APPLICATION | Student … | Father … | Class … | Mobile …`.
- **Colours** – the default theme is blue/gold. If you pick custom colours in Website settings → Branding, they override it.

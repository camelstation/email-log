# Email Log

An email-driven website for logging whatever I want. I send myself an email. It can include a link or a photo. The email becomes an chronological entry on a public website, updated automatically and hosted on GitHub Pages. All content lives in a single JSON file committed to the repo.

---

## Core behavior

- Emails are sent to a dedicated inbox
- A scheduled GitHub Action polls the inbox
- Emails containing commands are processed
- Entries are written to `entries.json`
- The static site reads and renders that file

---

## Email commands

### Add an entry

Include `[add]` anywhere in the email body.

Example:

[add] Happy New Year!

What happens:
- The email’s received date becomes the entry date (`YYYY-MM-DD`)
- The email body (with `[add]` removed) becomes the entry text
- If a URL is present, it is removed from the text and rendered as `[link]`
- If a photo is attached, it is uploaded to Cloudinary and rendered as `[photo]`
- The email subject (if present) is treated as a category

### Delete an entry

Include `[delete]` in the email body.

Example:

[delete] Happy New Year!

What happens:
- The system deletes the **most recent entry** whose normalized text matches exactly
- Date and category are ignored for matching
- If the entry had a photo, the Cloudinary image is deleted

---

## Security model

- Only emails **from one allowed sender address** are processed
- All other emails are ignored
- Emails without `[add]` or `[delete]` are ignored
- Processed emails are marked as read and labeled to prevent reprocessing

This keeps the system simple and safe.

---

## Repository structure

email-log/
├─ docs/ # GitHub Pages site root
│ ├─ index.html
│ ├─ app.js # Renders entries
│ ├─ style.css # Visual styling
│ ├─ settings.json # Theme + layout config
│ └─ data/
│ └─ entries.json # All log entries
│
├─ scripts/
│ ├─ ingest.py # Email ingestion + processing
│ └─ auth_local.py # One-time OAuth setup
│
├─ .github/
│ └─ workflows/
│ └─ ingest.yml # Scheduled GitHub Action
│
├─ requirements.txt
└─ README.md

---

## How the system works

### 1. Email ingestion

- A GitHub Action runs on a schedule
- It uses the Gmail API to read unread emails
- Messages are filtered by sender and command
- Content is parsed (text, links, attachments)

### 2. Photo handling

- If an email contains an image attachment:
  - The image is uploaded to Cloudinary
  - The returned URL is stored in the entry
- On deletion, the image is also deleted from Cloudinary

### 3. Data storage

- All entries live in `docs/data/entries.json`
- Entries are ordered newest-first
- Each entry has a unique internal ID
- The file is updated atomically and committed back to GitHub

### 4. Static site rendering

- `app.js` fetches:
  - `settings.json` (theme + layout)
  - `entries.json` (content)
- Entries are rendered line-by-line
- No build step, no framework and no runtime dependencies

---

## Customization

All visual changes are controlled from `settings.json` and CSS.

You can:
- Change the site title and footer text
- Switch between solid color, image, or gradient backgrounds
- Adjust fonts, colors, and spacing
- Map categories to emojis

No JavaScript changes are required for most aesthetic tweaks.

---

## How to repeat this yourself

### Required accounts
- GitHub (for repository + Pages)
- Gmail (dedicated inbox)
- Google Cloud project (Gmail API only)
- Cloudinary (optional, for photos)

### High-level steps
1. Create a GitHub repo and enable Pages from `/docs`
2. Create a Gmail inbox for log entries
3. Enable Gmail API in Google Cloud
4. Create OAuth credentials and generate a token
5. Store credentials as GitHub Secrets
6. Configure the ingestion GitHub Action
7. Send yourself an email with `[add]`

---

## Why did I do this

Because I wanted something simple to keep a track of things that is easy to update, free, extremely low maintenance and easy to audit and modify. I'm also becoming more forgetful and this seems like a nice way to keep a track of things that are important or of interest to me, both fleeting and more permanent. If you find yourself on this page, good for you.

---

## License

MIT

---

Made for people who like writing, systems, and quiet tools.

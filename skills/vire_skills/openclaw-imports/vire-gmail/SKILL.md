---
name: vire-gmail
description: "Use when configuring Gmail SMTP or IMAP with GMAIL_USER and an App Password."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [gmail, email, smtp, imap, app-password]
    related_skills: [vire, vire-n8n-automation]
---

# Vire — Gmail & Email Management

## Gmail App Password Setup

If your account supports App Passwords, store the SMTP/IMAP credentials in a private environment file under `HERMES_REALM_HOME/secrets/`:
```bash
GMAIL_USER=your-email@example.com
GMAIL_APP_PASSWORD=<16-char-app-password>
```

If authentication fails, verify account policy, credentials, and provider settings before changing code. Rotate credentials through the account's normal security flow.

## Send Email via SMTP
```python
import smtplib
import os
from email.mime.text import MIMEText

USER = os.environ["GMAIL_USER"]
PASSWD = os.getenv("GMAIL_APP_PASSWORD")

msg = MIMEText("Body", _charset="utf-8")
msg["Subject"] = "Subject"
msg["From"] = USER
msg["To"] = "recipient@example.com"

with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
    s.starttls()
    s.login(USER, PASSWD)
    s.sendmail(USER, [msg["To"]], msg.as_string())
```

## Gmail App Password Stale/Failure Pattern (Pitfall)

**Symptom:** IMAP works (can read inbox fine), but SMTP fails with `535 BadCredentials` or similar.

**Cause:** Credentials, account policy, or provider settings may have changed.

**Triage:**
1. Verify IMAP reads still work (`imaplib.IMAP4_SSL` login succeeds)
2. Try SMTP login (`smtplib.SMTP` with `starttls()` + `login()`)
3. If SMTP fails but IMAP works, check SMTP-specific settings and credential status
4. Rotate the App Password through the provider's normal security flow if required
5. Update `~/.config/hermes-realm/secrets/gmail.env` with the fresh password
6. Re-test SMTP send immediately after

App Password validity depends on the account's current security configuration.

**Prevention:** Test IMAP and SMTP separately with explicit operator approval before enabling automated sending.

## Read Inbox via IMAP
```python
import imaplib, email
from email.header import decode_header

with imaplib.IMAP4_SSL("imap.gmail.com", timeout=15) as imap:
    imap.login(USER, PASSWD)
    imap.select("inbox")
    _, data = imap.search(None, "ALL")
    for msg_id in data[0].split()[-20:]:
        _, raw = imap.fetch(msg_id, "(RFC822)")
        msg = email.message_from_bytes(raw[0][1])
        print(msg.get("Subject"), msg.get("From"))
```

## Auto-Reply Rules

Configured in N8N workflow `gmail-autoresponder`. Triggers on unread messages matching keywords (order, shipping, inventory). See the `vire-n8n-automation` skill.

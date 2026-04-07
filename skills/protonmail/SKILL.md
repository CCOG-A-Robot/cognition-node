---
name: protonmail
description: Access, read, and reply to emails on ProtonMail using the agent-browser tool. Used for managing the corporate/autonomous email account SamsonClaw@proton.me.
read_when:
  - The user asks to check email
  - The user asks to send an email via ProtonMail
  - Managing SamsonClaw@proton.me
---

# ProtonMail Operations

Due to ProtonMail's end-to-end encryption, standard IMAP/SMTP tools cannot be used natively without a local bridge. Therefore, we use **agent-browser** to interact directly with the web interface.

## Credentials
Check `TOOLS.md` for the current ProtonMail credentials (Email, Password).

## Standard Workflow

### 1. Login
```bash
# Open the login page
agent-browser open https://mail.proton.me/login

# Wait for load, snapshot to find input references
agent-browser wait 5000 && agent-browser snapshot

# Fill credentials and login (adjust @ref based on snapshot, usually role "textbox")
agent-browser fill "textbox[name='username']" "SamsonClaw"
agent-browser fill "textbox[name='password']" "<PASSWORD>"
agent-browser click "button:has-text('Sign in')"
```

### 2. Bypassing Modals
ProtonMail often loads onboarding modals, "Upgrade Storage" popups, or "Welcome" dialogues on first login. 
- Take a `snapshot` after login.
- Look for dialog buttons like `button "Maybe later"`, `button "Close"`, or `button "Next"`.
- Click them until the main inbox is visible (`heading "Inbox"` or `region "Message list"`).

### 3. Reading Emails
- Find the unread email in the `region "Message list"`.
- Click the heading or the region itself.
- E.g., `agent-browser click "heading:has-text('Email Subject')"`
- Wait for the email body to load (`agent-browser wait 3000`).
- Use `agent-browser eval "document.querySelectorAll('iframe')[0].contentDocument.body.innerText"` to extract the email content (since ProtonMail renders emails inside an iframe to isolate trackers).

### 4. Sending/Replying to Emails
- Click the Reply button: `agent-browser click "button:has-text('Reply')"`
- Wait for the composer to load.
- Focus the rich text editor iframe and type the message:
  ```bash
  agent-browser eval "document.querySelector('iframe[title=\"Email composer\"]').contentDocument.body.focus()"
  agent-browser keyboard inserttext "Your reply message here."
  ```
- Click Send:
  ```bash
  agent-browser click "button[data-testid='composer:send-button']"
  # Or find the Send button via snapshot (e.g., button "Send")
  ```

### 5. Cleanup
Always close the browser when finished to free up system memory:
```bash
agent-browser close
```
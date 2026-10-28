# ShamaTech Contact Rate Limiting

## Implementation

The contact CGI endpoint uses server/contact_guard.py.

The guard executes before CGI response headers and before
the existing contact database and email notification functions.

## Protection

- Maximum 3 attempts per client IP per rolling 60 minutes.
- HTTP 429 with Retry-After when the limit is reached.
- Persistent SQLite storage with atomic transactions.
- Server-side input validation and honeypot protection.
- Rejected requests do not create contact inquiries.
- Rate limits apply across all website languages.

## Production configuration

Runtime state:
  /var/lib/shamatech/

Production CGI:
  /var/www/shama-tech-backend/server/cgi-bin/api

Production guard:
  /var/www/shama-tech-backend/server/contact_guard.py

The production CGI shebang uses the deployment virtual
environment. Preserve this when deploying from Git.

The SQLite database and HMAC key must remain private
and writable by the CGI user.

Never commit:
- SMTP credentials
- .env files
- SQLite runtime databases
- Rate-limit HMAC secrets
- SSL private keys

## Deployment

Backend changes must be deployed before frontend changes
that depend on new contact-form fields.

Preserve production configuration and runtime data.

Verify the following after deployment:
- API health
- Contact submission
- Email notification
- HTTP 400 validation
- HTTP 429 rate limiting
- Retry-After response header

Do not trigger real contact notifications during
automated rate-limit testing.

Guard unit tests are maintained in the ShamaTech frontend
repository under backend/contact-rate-limit/tests.

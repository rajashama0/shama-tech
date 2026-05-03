import html
import importlib.util
import os
import smtplib
import ssl
from email.message import EmailMessage


def email_config():
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "config.py")
    )

    spec = importlib.util.spec_from_file_location("config", path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)

    return config


def clean_value(value):
    if value is None:
        return ""
    return str(value).strip()


def send_contact_notification(contact_id, contact):
    config = email_config()

    if not int(getattr(config, "CONTACT_EMAIL_ENABLED", 0)):
        return {
            "status": 1,
            "sent": 0,
            "reason": "email notifications disabled",
        }

    required_config = {
        "SMTP_HOST": getattr(config, "SMTP_HOST", ""),
        "SMTP_PORT": getattr(config, "SMTP_PORT", ""),
        "SMTP_USER": getattr(config, "SMTP_USER", ""),
        "SMTP_PASSWORD": getattr(config, "SMTP_PASSWORD", ""),
        "SMTP_FROM_EMAIL": getattr(config, "SMTP_FROM_EMAIL", ""),
        "CONTACT_NOTIFY_EMAIL": getattr(config, "CONTACT_NOTIFY_EMAIL", ""),
    }

    missing = []
    for key, value in required_config.items():
        if clean_value(value) == "":
            missing.append(key)

    if missing:
        return {
            "status": 0,
            "sent": 0,
            "reason": "missing email config: " + ",".join(missing),
        }

    full_name = clean_value(contact.get("full_name", ""))
    company_name = clean_value(contact.get("company_name", ""))
    email = clean_value(contact.get("email", ""))
    phone = clean_value(contact.get("phone", ""))
    service_interest = clean_value(contact.get("service_interest", ""))
    budget_range = clean_value(contact.get("budget_range", ""))
    message = clean_value(contact.get("message", ""))
    source_page = clean_value(contact.get("source_page", ""))

    subject = f"New Shama Tech contact form submission #{contact_id}"

    text_body = f"""New Shama Tech contact form submission

ID: {contact_id}
Full name: {full_name}
Company: {company_name}
Email: {email}
Phone: {phone}
Service interest: {service_interest}
Budget range: {budget_range}
Source page: {source_page}

Message:
{message}
"""

    html_body = f"""
<html>
  <body>
    <h2>New Shama Tech contact form submission</h2>

    <table cellpadding="6" cellspacing="0" border="1">
      <tr>
        <td><b>ID</b></td>
        <td>{html.escape(str(contact_id))}</td>
      </tr>
      <tr>
        <td><b>Full name</b></td>
        <td>{html.escape(full_name)}</td>
      </tr>
      <tr>
        <td><b>Company</b></td>
        <td>{html.escape(company_name)}</td>
      </tr>
      <tr>
        <td><b>Email</b></td>
        <td>{html.escape(email)}</td>
      </tr>
      <tr>
        <td><b>Phone</b></td>
        <td>{html.escape(phone)}</td>
      </tr>
      <tr>
        <td><b>Service interest</b></td>
        <td>{html.escape(service_interest)}</td>
      </tr>
      <tr>
        <td><b>Budget range</b></td>
        <td>{html.escape(budget_range)}</td>
      </tr>
      <tr>
        <td><b>Source page</b></td>
        <td>{html.escape(source_page)}</td>
      </tr>
    </table>

    <h3>Message</h3>
    <p>{html.escape(message).replace(chr(10), "<br>")}</p>
  </body>
</html>
"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.SMTP_FROM_EMAIL
    msg["To"] = config.CONTACT_NOTIFY_EMAIL

    if email != "":
        msg["Reply-To"] = email

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        smtp_host = config.SMTP_HOST
        smtp_port = int(config.SMTP_PORT)
        smtp_use_tls = int(getattr(config, "SMTP_USE_TLS", 1))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
            if smtp_use_tls:
                smtp.starttls(context=ssl.create_default_context())

            smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
            smtp.send_message(msg)

        return {
            "status": 1,
            "sent": 1,
            "reason": "sent",
        }

    except Exception as e:
        return {
            "status": 0,
            "sent": 0,
            "reason": str(e),
        }
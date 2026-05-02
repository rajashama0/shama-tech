import re
import importlib.util
import os
import boto3
from botocore.exceptions import ClientError


CONTACT_STATUSES = ["new", "reviewed", "contacted", "closed", "spam"]


def contact_config():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.py"))
    spec = importlib.util.spec_from_file_location("config", path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    return config


def clean_str(v):
    return str(v).strip()


def email_ok(email):
    if len(email) > 255:
        return 0
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if re.match(pattern, email):
        return 1
    return 0


def contact_chk(i):
    config = contact_config()
    full_name = clean_str(i.get("full_name", ""))
    company_name = clean_str(i.get("company_name", ""))
    email = clean_str(i.get("email", ""))
    phone = clean_str(i.get("phone", ""))
    service_interest = clean_str(i.get("service_interest", ""))
    budget_range = clean_str(i.get("budget_range", ""))
    message = clean_str(i.get("message", ""))
    source_page = clean_str(i.get("source_page", ""))

    if full_name == "":
        return {"status": 0, "err": "full_name is required", "field": "full_name"}
    if email == "":
        return {"status": 0, "err": "email is required", "field": "email"}
    if not email_ok(email):
        return {"status": 0, "err": "email is invalid", "field": "email"}
    if service_interest == "":
        return {"status": 0, "err": "service_interest is required", "field": "service_interest"}
    if message == "":
        return {"status": 0, "err": "message is required", "field": "message"}
    if len(message) > config.CONTACT_MESSAGE_MAX:
        return {"status": 0, "err": "message is too long", "field": "message"}
    if len(full_name) > 255:
        return {"status": 0, "err": "full_name is too long", "field": "full_name"}
    if len(company_name) > 255:
        return {"status": 0, "err": "company_name is too long", "field": "company_name"}
    if len(service_interest) > 255:
        return {"status": 0, "err": "service_interest is too long", "field": "service_interest"}
    if len(budget_range) > 100:
        return {"status": 0, "err": "budget_range is too long", "field": "budget_range"}
    if len(source_page) > 255:
        return {"status": 0, "err": "source_page is too long", "field": "source_page"}

    obj = {
        "full_name": full_name,
        "company_name": company_name,
        "email": email,
        "phone": phone,
        "service_interest": service_interest,
        "budget_range": budget_range,
        "message": message,
        "source_page": source_page,
        "status": "new",
    }
    return {"status": 1, "obj": obj}


def contact_add(i):
    chk = contact_chk(i)
    if not chk["status"]:
        return chk
    
    # Send email using AWS SES
    try:
        ses_client = boto3.client('ses', region_name='eu-north-1')  # Stockholm region
        subject = 'New Contact Form Submission'
        body = f"""
New contact form submission:

Full Name: {chk['obj']['full_name']}
Company Name: {chk['obj']['company_name']}
Email: {chk['obj']['email']}
Phone: {chk['obj']['phone']}
Service Interest: {chk['obj']['service_interest']}
Budget Range: {chk['obj']['budget_range']}
Message: {chk['obj']['message']}
Source Page: {chk['obj']['source_page']}
"""
        response = ses_client.send_email(
            Source='contact@shama-tech.com',  # Sender email
            Destination={
                'ToAddresses': ['contact@shama-tech.com']
            },
            Message={
                'Subject': {
                    'Data': subject
                },
                'Body': {
                    'Text': {
                        'Data': body
                    }
                }
            }
        )
        return {"status": 1, "id": response['MessageId']}
    except ClientError as e:
        return {"status": 0, "err": f"Email sending failed: {str(e)}"}


def contact_list():
    from tools.sql import find_in_sql

    w = find_in_sql({
        "table": "contact_submissions",
        "fld": "is_active",
        "val": 1,
        "what": "id,full_name,company_name,email,phone,service_interest,budget_range,message,source_page,status,created_at",
        "all": 1,
        "sort": "created_at",
        "desc": 1,
    })
    if type(w) is bool:
        return []
    ans = []
    for x in w:
        ans.append({
            "id": x[0],
            "full_name": x[1],
            "company_name": x[2],
            "email": x[3],
            "phone": x[4],
            "service_interest": x[5],
            "budget_range": x[6],
            "message": x[7],
            "source_page": x[8],
            "status": x[9],
            "created_at": str(x[10]),
        })
    return ans


def contact_status(id, status):
    from tools.sql import insert_to_sql

    status = clean_str(status)
    if status not in CONTACT_STATUSES:
        return {"status": 0, "err": "status is invalid", "field": "status"}
    res = insert_to_sql({
        "table": "contact_submissions",
        "id": int(id),
        "set": {"status": status},
    })
    if not res["status"]:
        return {"status": 0, "err": "status update failed"}
    return {"status": 1, "id": int(id), "contact_status": status}

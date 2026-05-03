from tools.db_contact_submissions import *
from tools.email_notify import *
from tools.kicapi import *


def api_contact_add(data):
    i = data["post"]["input"]

    res = contact_add(i)

    if not res["status"]:
        api_fail("validation_error", res["err"], {"field": res.get("field", "")})
        return

    email_res = send_contact_notification(res["id"], res["obj"])

    return api_success({
        "id": res["id"],
        "status": "new",
        "email_notification": {
            "sent": email_res.get("sent", 0),
            "reason": email_res.get("reason", ""),
        },
    })
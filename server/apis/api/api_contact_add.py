from tools.db_contact_submissions import *
from tools.kicapi import *


def api_contact_add(data):
    i = data["post"]["input"]
    res = contact_add(i)
    if not res["status"]:
        api_fail("validation_error", res["err"], {"field": res.get("field", "")})
        return
    api_success({
        "id": res["id"],
        "status": "new",
    })
    return

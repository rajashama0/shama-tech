from tools.db_admin import *
from tools.db_case_studies import *
from tools.kicapi import *


def api_admin_case_add(data):
    if not admin_allowed(data):
        api_fail("unauthorized", "admin token is missing or invalid")
        return
    i = data["post"]["input"]
    res = case_study_add(i)
    if not res["status"]:
        api_fail("validation_error", res["err"], {"field": res.get("field", "")})
        return
    api_success(res)
    return

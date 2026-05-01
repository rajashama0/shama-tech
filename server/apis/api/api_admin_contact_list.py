from tools.db_admin import *
from tools.db_contact_submissions import *
from tools.kicapi import *


def api_admin_contact_list(data):
    if not admin_allowed(data):
        api_fail("unauthorized", "admin token is missing or invalid")
        return
    api_success(contact_list())
    return

from tools.db_case_studies import *
from tools.kicapi import *


def api_case_study_get(data):
    i = data["post"]["input"]
    slug = str(i.get("slug", "")).strip()
    if slug == "":
        api_fail("validation_error", "slug is required", {"field": "slug"})
        return
    obj = case_study_get(slug, 1)
    if obj == {}:
        api_fail("not_found", "case study not found")
        return
    api_success(obj)
    return

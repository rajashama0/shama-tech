from tools.sql import *


def service_obj(x):
    return {
        "id": x[0],
        "name": x[1],
        "slug": x[2],
        "short_description": x[3],
        "long_description": x[4],
        "icon_key": x[5],
        "display_order": x[6],
    }


def services_list():
    w = find_in_sql({
        "table": "services",
        "fld": "is_active",
        "val": 1,
        "what": "id,name,slug,short_description,long_description,icon_key,display_order",
        "all": 1,
        "sort": "display_order",
    })
    if type(w) is bool:
        return []
    ans = []
    for x in w:
        ans.append(service_obj(x))
    return ans

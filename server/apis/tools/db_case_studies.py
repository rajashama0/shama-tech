import json
import re


def case_study_obj(x):
    tech = []
    if x[7] not in ["", None]:
        try:
            tech = json.loads(x[7])
        except Exception:
            tech = []
    return {
        "id": x[0],
        "title": x[1],
        "slug": x[2],
        "client_name": x[3],
        "industry": x[4],
        "problem": x[5],
        "solution": x[6],
        "technologies": tech,
        "outcome": x[8],
        "image_url": x[9],
        "is_published": x[10],
        "display_order": x[11],
    }


def slug_clean(v):
    v = str(v).strip().lower()
    v = re.sub(r"[^a-z0-9]+", "-", v)
    v = v.strip("-")
    return v


def case_studies_list(public_only=1):
    from tools.sql import find_in_sql

    where = {"is_active": 1}
    if public_only:
        where["is_published"] = 1
    w = find_in_sql({
        "table": "case_studies",
        "where": where,
        "what": "id,title,slug,client_name,industry,problem,solution,technologies,outcome,image_url,is_published,display_order",
        "all": 1,
        "sort": "display_order",
    })
    if type(w) is bool:
        return []
    ans = []
    for x in w:
        ans.append(case_study_obj(x))
    return ans


def case_study_get(slug, public_only=1):
    from tools.sql import find_in_sql

    where = {"slug": slug, "is_active": 1}
    if public_only:
        where["is_published"] = 1
    w = find_in_sql({
        "table": "case_studies",
        "where": where,
        "what": "id,title,slug,client_name,industry,problem,solution,technologies,outcome,image_url,is_published,display_order",
    })
    if type(w) is bool:
        return {}
    return case_study_obj(w)


def case_study_chk(i, partial=0):
    required = ["title", "problem", "solution", "outcome"]
    if not partial:
        for f in required:
            if str(i.get(f, "")).strip() == "":
                return {"status": 0, "err": f"{f} is required", "field": f}

    obj = {}
    fields = [
        "title",
        "slug",
        "client_name",
        "industry",
        "problem",
        "solution",
        "outcome",
        "image_url",
        "display_order",
        "is_published",
    ]
    for f in fields:
        if f in i:
            obj[f] = i[f]

    if "title" in obj and "slug" not in obj:
        obj["slug"] = slug_clean(obj["title"])
    if "slug" in obj:
        obj["slug"] = slug_clean(obj["slug"])
        if obj["slug"] == "":
            return {"status": 0, "err": "slug is required", "field": "slug"}
    if "technologies" in i:
        tech = i["technologies"]
        if type(tech) is str:
            tech = [tech]
        if type(tech) is not list:
            return {"status": 0, "err": "technologies must be a list", "field": "technologies"}
        obj["technologies"] = json.dumps(tech, ensure_ascii=False)
    if "display_order" in obj:
        obj["display_order"] = int(obj["display_order"])
    if "is_published" in obj:
        obj["is_published"] = int(obj["is_published"])

    return {"status": 1, "obj": obj}


def case_study_add(i):
    from tools.sql import insert_to_sql

    chk = case_study_chk(i)
    if not chk["status"]:
        return chk
    res = insert_to_sql({"table": "case_studies", "set": chk["obj"]})
    if not res["status"]:
        return {"status": 0, "err": "case study save failed"}
    return {"status": 1, "id": res["id"]}


def case_study_update(id, i):
    from tools.sql import insert_to_sql

    chk = case_study_chk(i, 1)
    if not chk["status"]:
        return chk
    if chk["obj"] == {}:
        return {"status": 0, "err": "no fields to update"}
    res = insert_to_sql({"table": "case_studies", "id": int(id), "set": chk["obj"]})
    if not res["status"]:
        return {"status": 0, "err": "case study update failed"}
    return {"status": 1, "id": int(id)}


def case_study_delete(id):
    from tools.sql import insert_to_sql

    res = insert_to_sql({
        "table": "case_studies",
        "id": int(id),
        "set": {"is_active": 0, "is_published": 0},
    })
    if not res["status"]:
        return {"status": 0, "err": "case study delete failed"}
    return {"status": 1, "id": int(id)}

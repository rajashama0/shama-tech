import importlib.util
import json
import os
import re
import sys
import traceback
from pathlib import Path
from urllib.parse import parse_qs

api_root = Path(__file__).resolve().parent
api_dir = api_root / "api"
server_dir = api_root.parent

sys.path.insert(0, str(api_root))
sys.path.insert(0, str(server_dir))

from tools.kicapi import *


def version():
    return "shama-tech.1"


def out_data():
    print(',"server_ver":"' + version() + '"')
    return


def read_par():
    qs = os.environ.get("QUERY_STRING", "")
    parsed = parse_qs(qs, keep_blank_values=True)
    par = {}
    for k in parsed:
        if parsed[k]:
            par[k] = parsed[k][0]
    return par


def read_post():
    raw = sys.stdin.read()
    if raw == "":
        return {"info": {"ses": "", "uses": "", "os": ""}, "input": {}}
    try:
        post = json.loads(raw)
    except Exception:
        return {"info": {"ses": "", "uses": "", "os": ""}, "input": {}, "bad_json": 1}
    if type(post) is not dict:
        return {"info": {"ses": "", "uses": "", "os": ""}, "input": {}, "bad_json": 1}
    if "info" not in post or type(post["info"]) is not dict:
        post["info"] = {"ses": "", "uses": "", "os": ""}
    if "input" not in post or type(post["input"]) is not dict:
        post["input"] = {}
    return post


def api_methods():
    ans = []
    for path in api_dir.glob("api_*.py"):
        ans.append(path.stem)
    return sorted(ans)


def public_methods():
    return [
        "api_health",
        "api_services",
        "api_case_studies",
        "api_case_study_get",
        "api_contact_add",
    ]


def admin_methods():
    return [
        "api_admin_contact_list",
        "api_admin_contact_status",
        "api_admin_case_add",
        "api_admin_case_update",
        "api_admin_case_delete",
    ]


def valid_method(meth):
    if not re.fullmatch(r"api_[a-z0-9_]+", meth):
        return 0
    if meth not in api_methods():
        return 0
    return 1


def admin_token():
    return os.environ.get("HTTP_X_ADMIN_TOKEN", "")


def admin_allowed():
    import config

    if config.ADMIN_API_KEY == "":
        return 0
    if admin_token() == config.ADMIN_API_KEY:
        return 1
    return 0


def load_api(meth):
    path = api_dir / f"{meth}.py"
    spec = importlib.util.spec_from_file_location(meth, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def do():
    par = read_par()
    post = read_post()
    meth = par.get("meth", "")
    print(f'"method":"{meth}"')

    if meth == "":
        api_fail("missing_method", "missing meth")
        return
    if post.get("bad_json", 0):
        api_fail("bad_json", "request body must be valid json")
        return
    if not valid_method(meth):
        api_fail("wrong_method", "wrong method")
        return
    if meth in admin_methods() and not admin_allowed():
        api_fail("unauthorized", "admin token is missing or invalid")
        return
    if meth not in public_methods() and meth not in admin_methods():
        api_fail("forbidden", "method is not allowed")
        return

    try:
        module = load_api(meth)
        foo = getattr(module, meth)
        data = {}
        data["par"] = par
        data["post"] = post
        data["env"] = os.environ
        data["ses_data"] = {}
        data["user_id"] = 0
        foo(data)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        api_fail("internal_error", "internal api error")
    return


print('{"server":{')
do()
out_data()
print("}}")

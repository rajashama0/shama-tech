import importlib.util
import json
import os
import re
from datetime import datetime

try:
    import mysql.connector
except Exception:
    mysql = None


sql_v = 3.0


def kic_config():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.py"))
    spec = importlib.util.spec_from_file_location("config", path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    return config


def db_error():
    return {"status": False, "err": "database_error"}


def kic_sql_connect():
    if mysql is None:
        raise RuntimeError("mysql-connector-python is not installed")
    config = kic_config()
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )


def close_db(cursor, connection):
    if cursor:
        cursor.close()
    if connection:
        connection.close()


def find_in_sql(r):
    connection = None
    cursor = None
    try:
        connection = kic_sql_connect()
        cursor = connection.cursor()
        c = 0
        table = r["table"]
        tableas = table if " " not in table else table.split(" ")[1]
        q = f"SELECT {sql_what(r['what'])} FROM {table} {sql_join(tableas, r)} WHERE "

        if "fld" in r:
            fld = r["fld"]
            g = "`"
            if "." in fld:
                g = ""
            q += f"{g}{fld}{g}={kic_geresh(r['val'])}"
            c = c + 1

        if "where" in r and r["where"] != {}:
            if c:
                q += " AND "
            q1, c1 = sql_where(r["where"])
            q += q1
            c = c + c1

        if "is_active" in r:
            if c:
                q += " AND "
            q += f"""is_active={int(r["is_active"])} """
            c = c + 1

        if not c:
            q += "1=1"
        if "grp" in r:
            q += f' GROUP BY {r["grp"]}'
        if "sortj" in r and r["sortj"] != "":
            q += f' ORDER BY {sql_sortj(r["sortj"])}'
        if "sort" in r:
            q += f' ORDER BY `{r["sort"]}`'
        if "desc" in r:
            q += " DESC"
        if "limit" in r:
            q += f' LIMIT {int(r["limit"])}'

        cursor.execute(q)
        results = cursor.fetchall()
        if results == []:
            return False
        if "all" in r:
            return results
        return results[0]
    except Exception:
        return False
    finally:
        close_db(cursor, connection)


def insert_to_sql(r):
    connection = None
    cursor = None
    tera_id = -1
    try:
        connection = kic_sql_connect()
        cursor = connection.cursor()
        setdata = ""
        set1 = sql_set(r["set"])

        if "data" in r:
            x = r["data"]
            y = json.dumps(x, ensure_ascii=False)
            z = sql_escape(y)
            setdata = f",data='{z}'"

        query = f"INSERT INTO {r['table']} SET {set1}{setdata}"
        if "id" in r:
            if setdata != "":
                return {"err": "data field is supported only for new records", "status": False}
            query = f"""UPDATE {r['table']} SET {set1} WHERE {sql_var('id', r['id'])} """

        cursor.execute(query)
        tera_id = cursor.lastrowid
        connection.commit()
        return {"results": [], "status": True, "ver": sql_v, "id": tera_id}
    except Exception:
        return db_error()
    finally:
        close_db(cursor, connection)


def count_in_sql(r):
    connection = None
    cursor = None
    try:
        connection = kic_sql_connect()
        cursor = connection.cursor()
        query = f"SELECT COUNT(id) FROM {r['table']} WHERE {sql_var(r['fld'], r['val'])}"
        cursor.execute(query)
        results = cursor.fetchall()
        if results == []:
            return False
        return results[0]
    except Exception:
        return False
    finally:
        close_db(cursor, connection)


def gen_data():
    z = find_in_sql({"table": "gen", "fld": "is_active", "val": 1, "what": "*", "all": 1})
    gen = {}
    if type(z) is bool:
        return gen
    for x in z:
        id = x[0]
        name = x[1]
        gd = x[6]
        gen[name] = {"id": id, "val": x[2]}
        if gd is not None and gd:
            gen[name]["data"] = json.loads(gd)
    return gen


def get_data(table, id, fld="id"):
    z = find_in_sql({"table": table, "fld": fld, "val": id, "what": "data"})
    obj = {}
    if type(z) is tuple and z[0] is not None:
        obj = json.loads(z[0])
    return obj


def add_to_data(table, id, fld1, val1=""):
    obj = get_data(table, id)
    if type(fld1) is str:
        obj[fld1] = val1
        if val1 == "!del":
            del obj[fld1]
    if type(fld1) is dict:
        for k in fld1:
            obj[k] = fld1[k]
    sobj = json.dumps(obj, ensure_ascii=False)
    setdata = sql_var("data", sobj)
    return insert_to_sql({"table": table, "set": setdata, "id": id})


def get_next_counter(field, type1, data={}):
    gen = gen_data()
    x = gen[f"{type1}_{field}"]
    c = int(x["val"]) + 1
    t = insert_to_sql({"table": "gen", "set": f"val1={c}", "id": x["id"]})
    if not t["status"]:
        return -1
    for k in data:
        add_to_data("gen", x["id"], k, data[k])
    return c


def kic_sql(q, elr=0):
    connection = None
    cursor = None
    try:
        connection = kic_sql_connect()
        cursor = connection.cursor()
        cursor.execute(q)
        rc = cursor.rowcount
        results = cursor.fetchall()
        connection.commit()
        if elr:
            return {"status": 1, "row_count": rc, "results": results}
        return results
    except Exception:
        if elr:
            return {"status": 0, "row_count": 0, "results": []}
        return []
    finally:
        close_db(cursor, connection)


def kic_sql_delete(r):
    q = f'delete from {r["table"]} where id={kic_geresh(r["id"])} limit 1'
    w = kic_sql(q, 1)
    if w["row_count"] > 0:
        return {"status": 1}
    return {"status": 0, "err": "not deleted"}


def sql_next(r):
    table = r["table"]
    id = 0
    if r["id"]:
        id = r["id"]
    if "is_active" not in r:
        r["is_active"] = 1

    q = f"select * from `{table}` where id>{int(id)}"
    if r["is_active"]:
        q += f""" AND is_active={int(r["is_active"])} """
    q += " order by id limit 1"

    dict = kic_sql(f"desc `{table}`")
    ans = kic_sql(q)
    if len(ans) == 0:
        return {"id": ""}
    return array2obj(ans[0], dict)


def sql_order(r):
    table = r["table"]
    id = 0
    if r["id"]:
        id = r["id"]
    if "is_active" not in r:
        r["is_active"] = 1

    q = f"select * from `{table}` where id>{int(id)}"
    q += f""" AND is_active={int(r["is_active"])} """
    if "where" in r:
        q += f""" AND {r["where"]}"""
    q += " order by id"

    dict = kic_sql(f"desc `{table}`")
    ans = kic_sql(q)
    for x in ans:
        yield array2obj(x, dict)


def array2obj(ary, dict):
    ans = {}
    for i in range(len(dict)):
        fld = dict[i][0]
        ans[fld] = ary[i]
    return ans


cache1 = {}


def dic_of_table(tab):
    global cache1
    if "dict" in cache1 and tab in cache1["dict"]:
        return cache1["dict"][tab]
    dict = kic_sql(f"desc `{tab}`")
    if "dict" not in cache1:
        cache1["dict"] = {}
    cache1["dict"][tab] = dict
    return dict


def is_gen_table(tab):
    g = gen_data()
    gtab = f"{tab}_tab"
    if gtab in g:
        gen_id = g[gtab]["id"]
        d = get_data("gen", gen_id)
        if "tab_type" in d and d["tab_type"] == "gen":
            return 1
    return 0


def kic_refine(x, v, cond):
    if "cln" in cond:
        for cln in cond["cln"]:
            v = v.replace(cln, "")
    if "toLower" in cond:
        v = v.lower()
    if "strip" in cond:
        v = v.strip()
    if "fill_zeros" in cond:
        v = str(v).zfill(cond["fill_zeros"])
    if v != "":
        if "min" in cond and len(v) < cond["min"]:
            return {"status": 0, "err": f"length of {x} too small"}
        if "max" in cond and len(v) > cond["max"]:
            return {"status": 0, "err": f"length of {x} too long"}
        if "exactly" in cond and len(v) != cond["exactly"]:
            return {"status": 0, "err": f"length of {x} must be {cond['exactly']}"}
        if "list" in cond and v not in cond["list"]:
            return {"status": 0, "err": f"{x} is not in allowed list"}
        if "regex" in cond and not re.search(cond["regex"], v):
            return {"status": 0, "err": f"content of {x} must comply to regex"}
        if "is" in cond:
            for ii in cond["is"]:
                if ii == "email" and not validate_email(v):
                    return {"status": 0, "err": "content not a valid email address"}
                if ii == "date/mdy":
                    v = validate_datemdy(v)
                if ii == "bool01":
                    if v in ["0", "1", 0, 1]:
                        v = int(v)
                    else:
                        return {"status": 0, "err": f"must be 0 or 1"}
                if ii == "phone":
                    v1 = v.replace("-", "")
                    if not re.fullmatch(r"\d{10}", v1):
                        return {"status": 0, "err": "phone format wrong", "errcode": 101}
    return v


def validate_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None


def validate_datemdy(v):
    d = v.split("/")
    day = int(d[1])
    mon = int(d[0])
    yir = int(d[2])
    y0 = int(datetime.today().strftime("%Y"))
    e = 0
    if day > 31 or day < 1:
        e = 1
    if mon > 12 or mon < 1:
        e = 2
    if yir > (y0 + 10) or yir < (y0 - 180):
        e = 3
    if e:
        return {"status": 0, "err": f"date wrong format ({e} / {y0})"}
    if day < 10:
        day = f"0{day}"
    if mon < 10:
        mon = f"0{mon}"
    return f"{yir}-{mon}-{day}"


def sql_escape(v):
    return str(v).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def kic_geresh(v):
    if type(v) is int or type(v) is float:
        return f"{v}"
    return f"'{sql_escape(v)}'"


def get_record(table, id, fld="id"):
    dict = kic_sql(f"desc `{table}`")
    z = find_in_sql({"table": table, "fld": fld, "val": id, "what": "*"})
    if type(z) is bool:
        return {}
    obj = array2obj(z, dict)
    jdata = get_data(table, id)
    obj = {**obj, **jdata}
    if "data" in obj:
        del obj["data"]
    return obj


def sql_var(k, v, c="="):
    r = ""
    if k in ["order", "key", "group", "limit", "from", "to"]:
        r = "`"
    if c == " in ":
        return f"{r}{k}{r}{c}{v}"
    if type(v) is int or type(v) is float:
        return f"{r}{k}{r}{c}{v}"
    if type(v) is dict:
        v = json.dumps(v, ensure_ascii=False)
    return f'{r}{k}{r}{c}"{sql_escape(v)}"'


def sql_set(obj):
    if type(obj) is str:
        return obj
    set1 = ""
    for k in obj:
        set1 += f",{sql_var(k, obj[k])}"
    return set1[1:]


def sql_where(obj):
    if type(obj) is str or type(obj) is int:
        return str(obj), 1
    set1 = ""
    c = 0
    for k in obj:
        vv = obj[k]
        v = vv
        con = "="
        key = k.split("/")[0]
        if type(vv) is tuple:
            con0 = vv[0]
            v = vv[1]
            con = f" {con0} "
            if con0 == "in":
                v = "(" + ",".join(map(str, v)) + ")"
            if con0 == "like":
                v = f"%{v}%"
            if len(vv) > 2:
                key = f"{vv[2]}->>'$.{key}'"
        set1 += f" AND {sql_var(key, v, con)}"
        c = c + 1
    return set1[5:], c


def sql_join(tableas, r):
    j = ""
    for typ in ("join/INNER", "ljoin/LEFT", "rjoin/RIGHT"):
        ty = typ.split("/")
        key = ty[0]
        side = ty[1]
        if key in r:
            for join in r[key]:
                jtab = join["jtab"]
                onj = join.get("jon", "id")
                on1 = join["on"]
                jtabas = jtab if " " not in jtab else jtab.split(" ")[1]
                j += f"{side} JOIN {jtab} ON {tableas}.{on1}={jtabas}.{onj} "
                if "And" in join:
                    j += f' AND {join["And"]}'
    return j


def sqd(key):
    return f"json_extract(data,'$.{key}')"


def sql_what(s):
    if ":" not in str(s):
        return s
    news = ""
    p = ""
    for one in str(s).split(","):
        if ":" in one:
            two = one.split(":")
            one = f'{two[0]}->>"$.{two[1]}"'
        news += p + one
        p = ","
    return news


def sql_sortj(s):
    if ":" not in s:
        return s
    sall = s.split(":")
    l = len(sall)
    s1 = sall[0]
    s2 = sall[1] if l > 1 else ""
    s3 = sall[2] if l > 2 else ""
    s = s1
    if s2:
        s = f'{s1}->>"$.{s2}"'
    if "int" in s3:
        s = f"CAST({s} as SIGNED INTEGER)"
    if "desc" in s3:
        s = f"{s} DESC"
    return s

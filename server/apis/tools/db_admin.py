import importlib.util
import os


def admin_config():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.py"))
    spec = importlib.util.spec_from_file_location("config", path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    return config


def admin_token(data):
    env = data.get("env", {})
    post = data.get("post", {})
    info = post.get("info", {})
    par = data.get("par", {})

    token = env.get("HTTP_X_ADMIN_TOKEN", "")
    if token != "":
        return token
    token = info.get("admin_token", "")
    if token != "":
        return token
    return par.get("admin_token", "")


def admin_allowed(data):
    config = admin_config()
    key = getattr(config, "admin_api_key", "")
    if key == "":
        return 0
    if admin_token(data) == key:
        return 1
    return 0

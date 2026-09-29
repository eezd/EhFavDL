import os

import yaml


class ConfigError(ValueError):
    """Raised when the application configuration is missing or invalid."""

def _parse_bool(value, field_name):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "on", "1"}:
            return True
        if normalized in {"false", "no", "off", "0"}:
            return False
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise ConfigError(f"Invalid boolean value for {field_name}: {value!r}")


def _parse_watch_fav_ids(value):
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple, set)):
        return ",".join(str(item).strip() for item in value if str(item).strip())
    return str(value)

class AppConfig:
    def __init__(self, config_path="./config.yaml"):
        self.config_path = os.path.abspath(config_path)
        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
        except FileNotFoundError as exc:
            raise ConfigError(f"Configuration file not found: {self.config_path}") from exc

        try:
            self.base_url = str(config["website"])
            self.data_path = str(config["data_path"])
            self.gallery_path = os.path.join(self.data_path, "gallery")
            self.web_path = os.path.join(self.data_path, "web")
            self.del_path = os.path.join(self.data_path, "del")
            self.duplicate_del_path = os.path.join(self.data_path, "duplicate_del")
            self.dbs_name = str(config["dbs_name"])
            self.tags_translation = _parse_bool(config["tags_translation"], "tags_translation")
            self.prefer_japanese_title = _parse_bool(config["prefer_japanese_title"], "prefer_japanese_title")
            self.connect_limit = int(config["connect_limit"])
            self.lan_url = str(config["lan_url"])
            self.lan_api_psw = str(config["lan_api_psw"])

            cookies = config["cookies"]
            self.eh_cookies = {
                "ipb_member_id": str(cookies["ipb_member_id"]),
                "ipb_pass_hash": str(cookies["ipb_pass_hash"]),
                "igneous": str(cookies["igneous"]),
            }
            for key in ("sk", "hath_perks"):
                if key in cookies:
                    self.eh_cookies[key] = str(cookies[key])

            proxy = config["proxy"]
            self.proxy_status = _parse_bool(proxy["enable"], "proxy.enable")
            self.proxy_url = str(proxy["url"])
            self.request_headers = {"User-Agent": config["User-Agent"]}
            self.watch_fav_ids = _parse_watch_fav_ids(config["watch_fav_ids"])
            self.watch_lan_status = _parse_bool(config["watch_lan_status"], "watch_lan_status")
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(f"Invalid configuration in {self.config_path}: {exc}") from exc

    @classmethod
    def load(cls, config_path="./config.yaml"):
        return cls(config_path)

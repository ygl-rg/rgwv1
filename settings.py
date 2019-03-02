import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = "/home/pi/rglog"
HOST = "esis.vip"
HTTP_PORT = 8001
URL_PREFIX = r'/rgw'
REDIS = {
    "host": "localhost",
    "port": 21999
}
WEB = {
    "static_path": "/home/pi/rgw_web",
    "export_path": "/home/pi/rglog",
    "login_page_bkg": "login_roundgis_bkg3.png",
    'js_dir': "rgw_js",
    'template_dir': "rgw_templates",
    'tpl_dir': "rgw_tpls",
    'css_dir': "rgw_css"
}

BIZ_DB = {
    "path": "/home/pi/rgw_biz.db3",
    "ttl": 3*86400
}

LOG_DB = {
    "path": "/home/pi/rgw_log.db3",
    "ttl": 3*86400
}


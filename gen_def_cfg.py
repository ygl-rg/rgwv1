import sys
import json

cfg_tbl = {
    "path": {
        "syslog": "/home/pi/rglog"
    },

    "host": "esis.vip",

    "http_port": 8001,

    'app_url_prefix': '/rgw/',

    "redis": {
        "host": "localhost",
        "port": 21999
    },

    'web': {
        "static_path": "/home/pi/rgw_web",
        "export_path": "/home/pi/rglog",
        "login_page_bkg": "login_roundgis_bkg3.png",
        'js_dir': "rgw_js",
        'template_dir': "rgw_templates",
        'tpl_dir': "rgw_tpls",
        'css_dir': "rgw_css"
    },

    'db': {
        "biz": {"db_path": "/home/pi/rgw_biz.db3", 'ttl': 3 * 86400},
        "log": {"db_path": "/home/pi/rgw_log.db3", 'ttl': 3 * 86400}
    }
}


def main(file_path):
    with open(file_path, 'w') as f:
        json.dump(cfg_tbl, f, indent=4)


if __name__ == "__main__":
    main(sys.argv[1])

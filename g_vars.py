import json

g_cfg = {}


def LoadConfig(file_path):
    global g_cfg
    with open(file_path, 'r') as f:
        g_cfg = json.load(f)
    if "login_page_bkg" not in g_cfg['web']:
        g_cfg['web']['login_page_bkg'] = ''
    if 'app_url_prefix' not in g_cfg:
        g_cfg['app_url_prefix'] = r'/rgw'


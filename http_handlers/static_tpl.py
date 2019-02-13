# -*- coding: utf-8 -*-
import os.path as os_path
import cyclone.web as cyclone_web
import g_vars
import rgw_consts


class AbstractHandler(cyclone_web.RequestHandler):
    def initialize(self, **kwargs):
        self.tpl_param_tbl = {}

    def get(self, path, include_body=True):
        self.SetExtraHeaders()
        tpl_name = path
        if tpl_name in self.tpl_param_tbl:
            self.render(tpl_name, **self.tpl_param_tbl[tpl_name])
        else:
            self.render(tpl_name)

    def SetExtraHeaders(self):
        raise NotImplementedError()


class JsHandler(AbstractHandler):
    def initialize(self, **kwargs):
        self.tpl_param_tbl = {
            'em_rpc.js': {
                'url': rgw_consts.Node_URLs.API_EM
            },

            'sys_cfg_rpc.js': {
                'url': rgw_consts.Node_URLs.API_SYS_CFG
            },

            'sensor_rpc.js': {
                'url': rgw_consts.Node_URLs.API_SENSOR_ADM
            },

            'switch_rpc.js': {
                'url': rgw_consts.Node_URLs.API_SWITCH_ADM
            },

            'sensor_trigger_rpc.js': {
                'url': rgw_consts.Node_URLs.API_SENSOR_TRIGGER
            }
        }

    def SetExtraHeaders(self):
        self.set_header('Content-Type', 'text/javascript')

    def get_template_path(self):
        return os_path.join(g_vars.g_cfg['web']['static_path'], g_vars.g_cfg['web']['js_dir'])


class CssHandler(AbstractHandler):
    def SetExtraHeaders(self):
        self.set_header('Content-Type', 'text/css')

    def get_template_path(self):
        return os_path.join(g_vars.g_cfg['web']['static_path'], g_vars.g_cfg['web']['css_dir'])


class DojoTplHandler(AbstractHandler):
    def SetExtraHeaders(self):
        self.set_header('Content-Type', 'text/html')

    def get_template_path(self):
        return os_path.join(g_vars.g_cfg['web']['static_path'], g_vars.g_cfg['web']['template_dir'])


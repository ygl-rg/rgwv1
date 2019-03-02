# -*- coding: utf-8 -*-
import os.path as os_path
import cyclone.web as cyclone_web
import settings
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
                'url': rgw_consts.URLs.API_EM
            },

            'sys_cfg_rpc.js': {
                'url': rgw_consts.URLs.API_SYS_CFG
            },

            'sensor_rpc.js': {
                'url': rgw_consts.URLs.API_SENSOR_ADM
            },

            'switch_rpc.js': {
                'url': rgw_consts.URLs.API_SWITCH_ADM
            },

            'sensor_trigger_rpc.js': {
                'url': rgw_consts.URLs.API_SENSOR_TRIGGER
            },

            'zb_module_rpc.js': {
                'url': rgw_consts.URLs.API_ZB_MODULE_ADM
            },

            'zb_device_rpc.js': {
                'url': rgw_consts.URLs.API_ZB_DEVICE_ADM
            }
        }

    def SetExtraHeaders(self):
        self.set_header('Content-Type', 'text/javascript')

    def get_template_path(self):
        return os_path.join(settings.WEB['static_path'], settings.WEB['js_dir'])


class CssHandler(AbstractHandler):
    def SetExtraHeaders(self):
        self.set_header('Content-Type', 'text/css')

    def get_template_path(self):
        return os_path.join(settings.WEB['static_path'], settings.WEB['css_dir'])


class DojoTplHandler(AbstractHandler):
    def SetExtraHeaders(self):
        self.set_header('Content-Type', 'text/html')

    def get_template_path(self):
        return os_path.join(settings.WEB['static_path'], settings.WEB['template_dir'])


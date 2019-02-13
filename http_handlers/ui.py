# -*- coding: utf-8 -*-
from twisted.internet import defer
from twisted.python import log
from cyclone import web as cyclone_web
from cyclone import escape as c_escape
import rg_lib
import rgw_consts
import multi_lang
import api_core
import api_req_limit
import api_auth
import node_models as models
import g_vars


class UIBase(cyclone_web.RequestHandler):
    async def async_get(self):
        raise NotImplementedError()

    async def async_post(self):
        raise NotImplementedError()

    def get(self):
        return defer.ensureDeferred(self.async_get())

    def post(self):
        return defer.ensureDeferred(self.async_post())


def DetectLoginPortal(req_handler):
    portal = req_handler.get_argument('loginportal', 'login')
    if portal == 'login':
        return rgw_consts.Node_URLs.APP_EM_LOGIN
    elif portal == 'login2':
        return rgw_consts.Node_URLs.APP_EM_LOGIN
    else:
        raise cyclone_web.HTTPError(404)


def GetToken(req_handler):
    sid = req_handler.get_cookie(rgw_consts.Cookies.TENANT)
    if sid:
        return sid
    else:
        return req_handler.get_argument('token', '')


def GetLangCode(req_handler):
    code = req_handler.get_argument('lang', None)
    if code is None:
        code = req_handler.get_cookie(rgw_consts.Cookies.USER_LANG, 'en')
    return rg_lib.Locale.GetLocale(code)


class AppAdmLogin(UIBase):
    def initialize(self, **kwargs):
        self.url_tbl = {'sensor': rgw_consts.Node_URLs.APP_ADM_SENSOR,
                        'switch': rgw_consts.Node_URLs.APP_ADM_SWITCH,
                        'sys_cfg': rgw_consts.Node_URLs.APP_SYS_CFG}

        self.adm_types = [{'name': 'Sensor/传感器', 'value': 'sensor'},
                          {'name': 'Switch/开关', 'value': 'switch', "checked": 1},
                          {'name': 'System Config/系统参数', 'value': 'sys_cfg'}]

    def RenderPage(self, user_lang, hint):
        self.render(rgw_consts.Node_TPL_NAMES.APP_ADM_LOGIN,
                    app_js_dir=g_vars.g_cfg['web']['js_dir'],
                    app_template_dir=g_vars.g_cfg['web']['template_dir'],
                    title="rgw adm",
                    hint=hint,
                    loginurl=rgw_consts.Node_URLs.APP_ADM_LOGIN,
                    bkgpng=g_vars.g_cfg['web']['login_page_bkg'],
                    user_lang=user_lang,
                    adm_types=self.adm_types)

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("AppAdmLogin", rg_lib.Cyclone.TryGetRealIp(self), 5)
            user_lang = self.get_cookie(rgw_consts.Cookies.USER_LANG, "eng")
            self.RenderPage(user_lang, '')
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_post(self):
        await api_req_limit.CheckMinuteRate("adm_login", rg_lib.Cyclone.TryGetRealIp(self), 5)
        pwd = self.get_argument('pwd', '').strip()
        adm_type = self.get_argument('adm_type', 'switch')
        user_lang = self.get_cookie(rgw_consts.Cookies.USER_LANG, "eng")
        if pwd:
            try:
                sessionid, expire_at, curr = await api_auth.Adm(pwd)
                self.set_cookie(rgw_consts.Cookies.TENANT, sessionid, expires=rg_lib.DateTime.ts2dt(expire_at),
                                httponly=True)
                if adm_type in self.url_tbl:
                    self.redirect(self.url_tbl[adm_type])
                else:
                    raise ValueError("adm type incorrect")
            except rg_lib.RGError as rge:
                if models.ErrorTypes.TypeOfNoRight(rge.message):
                    self.RenderPage(user_lang, "no right")
                elif models.ErrorTypes.TypeOfPwdErr(rge):
                    self.RenderPage(user_lang, 'password error')
                elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                    self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
                else:
                    self.RenderPage(user_lang, 'server error')
            except Exception:
                log.err()
                self.RenderPage(user_lang, 'server error')
        else:
            await self.async_get()


class AppLoginBase(UIBase):
    def RenderPage(self, hint_str):
        ulang = GetLangCode(self)
        app_opts = self.GetAppOptions()[ulang]
        self.render(rgw_consts.Node_TPL_NAMES.APP_LOGIN,
                    app_js_dir=g_vars.g_cfg['web']['js_dir'],
                    app_template_dir=g_vars.g_cfg['web']['template_dir'],
                    title=self.GetTitle(),
                    hint=hint_str, loginurl=self.GetLoginUrl(), bkgpng=g_vars.g_cfg['web']['login_page_bkg'],
                    user_lang=ulang, lang_options=self.GetLangOptions(), app_options=app_opts)

    def GetLangOptions(self):
        return [{"label": "ENG", "value": "en"},
                {"label": "简体中文", "value": "zh-cn"},
                {'label': "繁體中文", "value": "zh-tw"}]

    def GetAppOptions(self):
        raise NotImplementedError()

    def GetTitle(self):
        raise NotImplementedError()

    def GotoPage(self):
        raise NotImplementedError()

    def GetLoginUrl(self):
        raise NotImplementedError()

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate(rg_lib.String.toutf8(self.GetLoginUrl()),
                                                    rg_lib.Cyclone.TryGetRealIp(self), 5)
            self.RenderPage("")
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_post(self):
        await api_req_limit.CheckMinuteRate("AppLoginBase", rg_lib.Cyclone.TryGetRealIp(self), 5)
        pwd = self.get_argument('pwd', '').strip()
        ulang = self.get_argument('user_lang', 'en')
        if pwd:
            try:
                sessionid, expire_at, curr = await api_auth.Adm(pwd)
                self.set_cookie(rgw_consts.Cookies.TENANT, sessionid, expires=rg_lib.DateTime.ts2dt(expire_at),
                                httponly=True)
                self.set_cookie(rgw_consts.Cookies.USER_LANG, ulang, httponly=True)
                self.GotoPage()
            except rg_lib.RGError as rge:
                if models.ErrorTypes.TypeOfPwdErr(rge):
                    self.RenderPage(models.MultiText.GetValue(multi_lang.password_error, ulang))
                elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                    self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
                else:
                    self.RenderPage(models.MultiText.GetValue(multi_lang.server_error, ulang))
            except Exception:
                log.err()
                self.RenderPage(models.MultiText.GetValue(multi_lang.server_error, ulang))
        else:
            await self.async_get()


class EmLogin(AppLoginBase):
    def GetTitle(self):
        return "Elastic Monitoring"

    def GetLoginUrl(self):
        return rgw_consts.Node_URLs.APP_EM_LOGIN

    def GetAppOptions(self):
        return {
            "en": [{'label': "Control/控制", "value": "em"},
                   {'label': 'Data/数据', "value": "em_sensor"}],

            "zh-cn": [{'label': "环境控制", "value": "em"},
                      {'label': "环境数据", "value": "em_sensor"}],

            "zh-tw": [{'label': "環境控制", "value": "em"},
                      {'label': "環境資訊", "value": "em_sensor"}]
        }

    def GotoPage(self):
        web_type = self.get_argument("web_type", "em")
        if web_type == "em":
            self.redirect(rgw_consts.Node_URLs.APP_EM)
        elif web_type == 'em_sensor':
            self.redirect(rgw_consts.Node_URLs.APP_EM_SENSOR)
        else:
            raise cyclone_web.HTTPError(404)


class ViewSwitchSchedule(UIBase):
    def GetTitle(self):
        return "Switch Schedules"

    def GetLabel(self):
        return {
            "en": {"remove": "remove", 'valid': "valid schedules", 'invalid': 'overdue schedules'},
            "zh-cn": {"remove": "删除", 'valid': "有效排程", 'invalid': "过期排程"},
            'zh-tw': {"remove": "移除", 'valid': "有效排程", 'invalid': "過期排程"}
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckMinuteRate("ViewSwitchSchedule", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = GetToken(self)
            ulang = GetLangCode(self)
            if sid:
                await api_auth.CheckRight(sid)
                label_tbl = self.GetLabel()[ulang]
                self.render(rgw_consts.Node_TPL_NAMES.VIEW_SWITCH_SCHEDULES,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            title=self.GetTitle(),
                            sessionid=sid, user_lang=ulang,
                            valid_label=label_tbl['valid'],
                            invalid_label=label_tbl['invalid'],
                            remove_label=label_tbl['remove'])
            else:
                login_url = DetectLoginPortal(self)
                self.redirect(login_url)
        except rg_lib.RGError as rge:
            if models.ErrorTypes.TypeOfNoRight(rge):
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
            elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except Exception:
            self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_get(self):
        await self.handlePage_()


class ViewSensorMinsAvgTrend(UIBase):
    def GetTitle(self):
        return "Sensor Data Trend"

    def GetMinsInterval(self):
        return [
            {"label": 1, 'value': 1},
            {"label": 2, "value": 2},
            {"label": 3, "value": 3},
            {"label": 5, "value": 5},
            {"label": 10, "value": 10, 'selected': True},
            {"label": 20, "value": 20},
            {"label": 30, "value": 30}
        ]

    async def handlePage_(self):
        try:
            await api_req_limit.CheckMinuteRate("ViewSensorMinsAvgTrend", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = GetToken(self)
            ulang = GetLangCode(self)
            temp_str = self.get_argument('sensorids')
            sensorids = c_escape.json_decode(c_escape.url_unescape(temp_str))
            if len(sensorids) < 1:
                raise cyclone_web.HTTPError(404, 'no sensor')
            if sid:
                await api_auth.CheckRight(sid)
                sql_str = rg_lib.Sqlite.GenInSql("""select COALESCE(name,'') name, id from rgw_sensor where id in """,
                                                 sensorids)
                sensors = await api_core.BizDB.Query([sql_str, sensorids])
                if len(sensors) > 0:
                    self.render(rgw_consts.Node_TPL_NAMES.VIEW_SENSOR_MINS_AVG_TREND,
                                app_js_dir=g_vars.g_cfg['web']['js_dir'],
                                app_css_dir=g_vars.g_cfg['web']['css_dir'],
                                app_template_dir=g_vars.g_cfg['web']['template_dir'],
                                title=self.GetTitle(),
                                sessionid=sid, user_lang=ulang,
                                sensorids=sensorids,
                                mins_interval_tbls=self.GetMinsInterval())
                else:
                    self.finish("no sensor")
            else:
                self.redirect(DetectLoginPortal(self))
        except rg_lib.RGError as rge:
            if models.ErrorTypes.TypeOfNoRight(rge):
                self.redirect(DetectLoginPortal(self))
            elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except cyclone_web.HTTPError:
            raise
        except Exception:
            log.err()
            self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_get(self):
        return await self.handlePage_()


class ViewSensorMinsAvgData(UIBase):
    def GetTitle(self):
        return "Sensor Data Log"

    def GetMinsInterval(self):
        return [
            {"label": 1, 'value': 1},
            {"label": 2, "value": 2},
            {"label": 3, "value": 3},
            {"label": 5, "value": 5},
            {"label": 10, "value": 10},
            {"label": 20, "value": 20, "selected": True},
            {"label": 30, "value": 30}
        ]

    async def handlePage_(self):
        try:
            await api_req_limit.CheckMinuteRate("ViewSensorMinsAvgData", rg_lib.Cyclone.TryGetRealIp(self))
            sid = GetToken(self)
            ulang = GetLangCode(self)
            temp = self.get_argument('ids', '')
            sensorids = c_escape.json_decode(c_escape.url_unescape(temp))
            if len(sensorids) < 1:
                raise cyclone_web.HTTPError(404, 'no sensor')
            if sid:
                await api_auth.CheckRight(sid)
                sql_str = rg_lib.Sqlite.GenInSql("""select COALESCE(name,'') name, id
                                                        from rgw_sensor where id in """,
                                                 sensorids)
                sensors = await api_core.BizDB.Query([sql_str, sensorids])
                sensors_tbl = {i['id']: i for i in sensors}
                if len(sensors) > 0:
                    self.render(rgw_consts.Node_TPL_NAMES.VIEW_SENSOR_MINS_AVG_DATA,
                                app_js_dir=g_vars.g_cfg['web']['js_dir'],
                                app_css_dir=g_vars.g_cfg['web']['css_dir'],
                                app_template_dir=g_vars.g_cfg['web']['template_dir'],
                                title=self.GetTitle(),
                                sessionid=sid, user_lang=ulang,
                                sensorids=sensorids,
                                sensors_tbl=sensors_tbl,
                                mins_interval_tbls=self.GetMinsInterval())
                else:
                    self.finish("no sensor")
            else:
                self.finish(rgw_consts.WebContent.PLEASE_LOGIN)
        except rg_lib.RGError as rge:
            if models.ErrorTypes.TypeOfNoRight(rge):
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
            elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except cyclone_web.HTTPError:
            raise
        except Exception:
            log.err()
            self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_get(self):
        return await self.handlePage_()


class ViewSwitchOnLogDetail(UIBase):
    def GetTitle(self):
        return "Switch On Duration Log Detail"

    def GetLabel(self):
        return {
            "en": {"remove": "remove", "refresh": "refresh", "query": "query"},
            "zh-cn": {"remove": "删除", "refresh": "刷新", "query": "查询"},
            "zh-tw": {"remove": "删除", "refresh": "刷新", "query": "查詢"}
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckMinuteRate("ViewSwitchOnLogDetail", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = GetToken(self)
            ulang = GetLangCode(self)
            temp = self.get_argument('switchid', '')
            if sid:
                await api_auth.CheckRight(sid)
                if len(temp) == 0:
                    raise cyclone_web.HTTPError(404, 'no switch')
                row = await api_core.Switch.Get(["select id, name from rgw_switch where id=?", (temp,)])
                if row is None:
                    raise cyclone_web.HTTPError(404, 'no switch')
                label_tbl = self.GetLabel()[ulang]
                self.render(rgw_consts.Node_TPL_NAMES.VIEW_SWITCH_ON_LOG_DETAIL,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            title=self.GetTitle(),
                            sessionid=sid, user_lang=ulang,
                            switchid=temp,
                            switch_name=row.get('name', ''),
                            query_btn_label=label_tbl['query'])
            else:
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
        except rg_lib.RGError as rge:
            if models.ErrorTypes.TypeOfNoRight(rge):
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
            elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except cyclone_web.HTTPError:
            raise
        except Exception:
            self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_get(self):
        return await self.handlePage_()


class ViewSensorRecentTrend(UIBase):
    def GetTitle(self):
        return "Sensor Data Recent Trend"

    def GetMinsInterval(self):
        return [
            {"label": 1, 'value': 1},
            {"label": 2, "value": 2},
            {"label": 3, "value": 3},
            {"label": 5, "value": 5},
            {"label": 10, "value": 10, 'selected': True},
            {"label": 20, "value": 20},
            {"label": 30, "value": 30}
        ]

    def GetHoursTbls(self):
        return [
            {"label": 1, 'value': 1},
            {"label": 3, "value": 3, 'selected': True},
            {"label": 6, "value": 6},
            {"label": 12, "value": 12},
            {"label": 18, "value": 18},
            {"label": 24, "value": 24}
        ]

    def GetLabelTbl(self):
        return {
            "en": {"hours": "hours", "minutes": "minutes"},
            "zh-cn": {"hours": "小时", "minutes": "分钟间隔"},
            "zh-tw": {"hours": "小時", "minutes": "分鐘間隔"}
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckMinuteRate("ViewSensorRecentTrend", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = GetToken(self)
            ulang = GetLangCode(self)
            temp_str = self.get_argument('sensorids')
            sensorids = c_escape.json_decode(c_escape.url_unescape(temp_str))
            plotting_no = self.get_argument('plotting_no', '1')
            if len(sensorids) < 1:
                raise cyclone_web.HTTPError(404, 'no sensor')
            if sid:
                await api_auth.CheckRight(sid)
                sql_str = rg_lib.Sqlite.GenInSql("""select COALESCE(name,'') name, id from rgw_sensor where id in """,
                                                 sensorids)
                sensors = await api_core.BizDB.Query([sql_str, sensorids])
                if len(sensors) > 0:
                    label_tbl = self.GetLabelTbl()[ulang]
                    self.render(rgw_consts.Node_TPL_NAMES.VIEW_SENSORS_RECENT_TREND,
                                app_js_dir=g_vars.g_cfg['web']['js_dir'],
                                app_css_dir=g_vars.g_cfg['web']['css_dir'],
                                app_template_dir=g_vars.g_cfg['web']['template_dir'],
                                title=self.GetTitle(),
                                sessionid=sid, user_lang=ulang,
                                sensorids=sensorids,
                                hours_tbls=self.GetHoursTbls(),
                                mins_interval_tbls=self.GetMinsInterval(),
                                hours_label=label_tbl['hours'],
                                minutes_label=label_tbl['minutes'],
                                plotting_no=plotting_no,
                                sensor_recent_hours_plotting_url=rgw_consts.Node_URLs.VIEW_RECENT_HOURS_SENSOR_DATA_PLOTTING[1:])
                else:
                    self.finish("no sensor")
            else:
                self.redirect(DetectLoginPortal(self))
        except rg_lib.RGError as rge:
            if models.ErrorTypes.TypeOfNoRight(rge):
                self.redirect(DetectLoginPortal(self))
            elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except cyclone_web.HTTPError:
            raise
        except Exception:
            log.err()
            self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_get(self):
        return await self.handlePage_()


class ViewMonthlySwitchUsage(UIBase):
    def GetTitle(self):
        return "Monthly Switch Usage"

    def GetLabel(self):
        return {
            "en": {"remove": "remove", "refresh": "refresh", "query": "query",
                   "export": "export excel"},
            "zh-cn": {"remove": "删除", "refresh": "刷新", "query": "查询",
                      "export": "导出(excel格式)"},
            "zh-tw": {"remove": "删除", "refresh": "刷新", "query": "查詢",
                      "export": "導出(EXCEL格式)"}
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckMinuteRate("ViewMonthlySwitchUsage", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = GetToken(self)
            ulang = GetLangCode(self)
            if sid:
                await api_auth.CheckRight(sid)
                label_tbl = self.GetLabel()[ulang]
                self.render(rgw_consts.Node_TPL_NAMES.VIEW_SWITCH_MONTHLY_USAGE,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            title=self.GetTitle(),
                            sessionid=sid, user_lang=ulang,
                            switch_on_detail_url=rgw_consts.Node_URLs.VIEW_SWITCH_ON_LOG_DETAIL[1:],
                            export_label=label_tbl['export'])
            else:
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
        except rg_lib.RGError as rge:
            if models.ErrorTypes.TypeOfNoRight(rge):
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
            elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except cyclone_web.HTTPError:
            raise
        except Exception:
            self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_get(self):
        return await self.handlePage_()


class AppEm(UIBase):
    def GetTitle(self):
        return "Elastic Monitoring"

    def GetLabel(self):
        return {
            "en": {"open": "turn on", "close": "turn off", "open_duration_desc": "15-9999 seconds",
                    'set_schedule': "set schedule",
                    'switch_schedule_view': "view schedule",
                    'set_cond_action_view': 'set action condition',
                    'switch_on_log_detail_view': "switch monthly usage",
                    'goto': 'env data'},
            "zh-cn": {"open": "打开", "close": "关闭", "open_duration_desc": "15-99999秒",
                      'set_schedule': "设置排程",
                      'switch_schedule_view': "查看排程",
                      'set_cond_action_view': '设置条件触发',
                      'switch_on_log_detail_view': "开关月统计",
                      'goto': '环境数据'},
            "zh-tw": {"open": "打開", "close": "關閉", "open_duration_desc": "15-99999秒",
                      'set_schedule': "设置排程",
                      'switch_schedule_view': "查看排程",
                      'set_cond_action_view': '設置條件觸發',
                      'switch_on_log_detail_view': "開關月統計",
                      'goto': '環境數據'}
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckMinuteRate("AppEm", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = self.get_cookie(rgw_consts.Cookies.TENANT)
            ulang = GetLangCode(self)
            if sid:
                await api_auth.CheckRight(sid)
                label_tbl = self.GetLabel()[ulang]
                self.render(rgw_consts.Node_TPL_NAMES.APP_EM,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            title=self.GetTitle(),
                            sessionid=sid, user_lang=ulang, open_valve_label=label_tbl['open'],
                            close_valve_label=label_tbl['close'],
                            open_duration_label=label_tbl['open_duration_desc'],
                            switch_schedule_view_url=rgw_consts.Node_URLs.VIEW_SWITCH_SCHEDULES[1:],
                            switch_schedule_view_label=label_tbl['switch_schedule_view'],
                            set_schedule_label=label_tbl['set_schedule'],
                            set_cond_action_view_label=label_tbl['set_cond_action_view'],
                            view_monthly_switch_usage_label=label_tbl['switch_on_log_detail_view'],
                            view_monthly_switch_usage_url=rgw_consts.Node_URLs.VIEW_MONTHLY_SWITCH_USAGE[1:],
                            set_sensor_trigger_view_url=rgw_consts.Node_URLs.APP_ADM_SENSOR_TRIGGER[1:],
                            em_sensor_url=rgw_consts.Node_URLs.APP_EM_SENSOR[1:],
                            goto_label=label_tbl['goto'])
            else:
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
        except rg_lib.RGError as rge:
            if models.ErrorTypes.TypeOfNoRight(rge):
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
            elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except Exception:
            log.err()
            self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_get(self):
        return await self.handlePage_()


class AppEmSensor(UIBase):
    def GetTitle(self):
        return "Elastic Monitoring"

    def GetLabel(self):
        return {
            "en": {'history_trend_url': 'history trend',
                   'history_data_url': 'history data',
                   'goto': 'env ctrl', 'plot1': 'plot1', 'plot2': 'plot2'},

            "zh-cn": {'history_trend_url': '历史趋势',
                      'history_data_url': '历史数据',
                      'goto': '环境控制', 'plot1': '趋势图1', 'plot2': '趋势图2'},
            "zh-tw": {'history_trend_url': '歷史趨勢',
                      'history_data_url': '歷史數據',
                      'goto': '环境控制', 'plot1': '趨勢图1', 'plot2': '趨勢图2'}
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckMinuteRate("AppEmSensor", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = self.get_cookie(rgw_consts.Cookies.TENANT)
            ulang = GetLangCode(self)
            if sid:
                await api_auth.CheckRight(sid)
                label_tbl = self.GetLabel()[ulang]
                self.render(rgw_consts.Node_TPL_NAMES.APP_EM_SENSOR,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            title=self.GetTitle(),
                            sessionid=sid, user_lang=ulang,
                            sensor_mins_avg_trend_url=rgw_consts.Node_URLs.VIEW_SENSOR_MINS_AVG_TREND[1:],
                            sensor_mins_avg_data_url=rgw_consts.Node_URLs.VIEW_SENSOR_MINS_AVG_DATA[1:],
                            sensor_recent_hours_plotting_url=rgw_consts.Node_URLs.VIEW_RECENT_HOURS_SENSOR_DATA_PLOTTING[1:],
                            sensor_recent_trend_url=rgw_consts.Node_URLs.VIEW_SENSORS_RECENT_TREND[1:],
                            em_url=rgw_consts.Node_URLs.APP_EM[1:],
                            goto_label=label_tbl['goto'],
                            plot1_label=label_tbl['plot1'],
                            plot2_label=label_tbl['plot2'],
                            history_trend_url_label=label_tbl['history_trend_url'],
                            history_data_url_label=label_tbl['history_data_url'])
            else:
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
        except rg_lib.RGError as rge:
            if models.ErrorTypes.TypeOfNoRight(rge):
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
            elif models.ErrorTypes.TypeOfAccessOverLimit(rge):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except Exception:
            self.finish(rgw_consts.WebContent.SERVER_ERROR)

    async def async_get(self):
        return await self.handlePage_()


class AppSysCfg(UIBase):
    def GetTimezoneOpts(self):
        import pytz
        asia_tzs = ['UTC']+[i for i in pytz.common_timezones if i.find('Asia') >= 0]
        return [{'label': i, 'value': i} for i in asia_tzs]

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("AppSysCfg", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = self.get_cookie(rgw_consts.Cookies.TENANT)
            if sid:
                await api_auth.CheckRight(sid)
                self.render(rgw_consts.Node_TPL_NAMES.APP_SYS_CFG,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            tz_options=self.GetTimezoneOpts(),
                            title="Sys Config", sessionid=sid)
            else:
                self.redirect(rgw_consts.Node_URLs.APP_ADM_LOGIN)
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            elif models.ErrorTypes.TypeOfNoRight(err):
                self.redirect(rgw_consts.Node_URLs.APP_ADM_LOGIN)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)


class AppSysCfgMobile(UIBase):
    def GetTimezoneOpts(self):
        import pytz
        asia_tzs = ['UTC']+[i for i in pytz.common_timezones if i.find('Asia') >= 0]
        return [{'label': i, 'value': i} for i in asia_tzs]

    def GetLabel(self):
        return {
            "en": {'save': 'Save',
                   'register': 'Register Devices',
                   'sync': 'Sync Devices',
                   'restart': 'Restart Service',
                   'reboot': 'Reboot Gateway',
                   'timezone': 'TimeZone',
                   'password': 'Password',
                   'email_sender': 'Email Sender'},
            "zh-cn": {'save': '保存',
                      'register': '注册设备',
                      'sync': '同步设备',
                      'restart': '重启服务',
                      'reboot': '重启网关',
                      'timezone': '时区',
                      'password': '密码',
                      'email_sender': '邮件发送人'
                      },
            'zh-tw': {'save': '保存',
                      'register': '註冊設備',
                      'sync': '同步設備',
                      'restart': '重啟服務',
                      'reboot': '重啟網關',
                      'timezone': '時區',
                      'password': '密碼',
                      'email_sender': '郵件發送人'
                      }
        }

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("AppSysCfgMobile", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = self.get_argument('token', '')
            ulang = GetLangCode(self)
            if sid:
                await api_auth.CheckRight(sid)
                label_tbl = self.GetLabel()[ulang]
                self.render(rgw_consts.Node_TPL_NAMES.APP_SYS_CFG_MOBILE,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            tz_options=self.GetTimezoneOpts(),
                            title="Sys Config", sessionid=sid,
                            register=label_tbl['register'],
                            sync=label_tbl['sync'],
                            save=label_tbl['save'],
                            restart=label_tbl['restart'],
                            reboot=label_tbl['reboot'],
                            timezone=label_tbl['timezone'],
                            password=label_tbl['password'],
                            email_sender=label_tbl['email_sender'],
                            user_lang=ulang)
            else:
                raise cyclone_web.HTTPError(403)
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            elif models.ErrorTypes.TypeOfNoRight(err):
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)


class AppEditSensor(UIBase):
    def GetDataNoTbls(self):
        return [{'value': i, 'label': i.replace('_', ' ')} for i in rgw_consts.SensorDataNo.LIST]

    def GetIconTbls(self):
        return [{'value': i, 'label': i.replace('_', ' ')} for i in rgw_consts.IconIds.SensorIcons()]

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("AppEditSensor", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = self.get_cookie(rgw_consts.Cookies.TENANT)
            if sid:
                await api_auth.CheckRight(sid)
                edit_mode = self.get_argument("edit_mode")
                if edit_mode == "edit":
                    rowid = self.get_argument("id")
                    self.render(rgw_consts.Node_TPL_NAMES.APP_EDIT_SENSOR,
                                app_js_dir=g_vars.g_cfg['web']['js_dir'],
                                app_css_dir=g_vars.g_cfg['web']['css_dir'],
                                app_template_dir=g_vars.g_cfg['web']['template_dir'],
                                title="Edit Sensor", sessionid=sid,
                                id=rowid, edit_mode=edit_mode,
                                data_no_tbls=self.GetDataNoTbls(),
                                iconid_tbls=self.GetIconTbls())
                else:
                    self.render(rgw_consts.Node_TPL_NAMES.APP_EDIT_SENSOR,
                                app_js_dir=g_vars.g_cfg['web']['js_dir'],
                                app_css_dir=g_vars.g_cfg['web']['css_dir'],
                                app_template_dir=g_vars.g_cfg['web']['template_dir'],
                                title="Add Sensor", sessionid=sid,
                                id=0, edit_mode=edit_mode,
                                data_no_tbls=self.GetDataNoTbls(),
                                iconid_tbls=self.GetIconTbls())
            else:
                self.finish("please login")
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            elif models.ErrorTypes.TypeOfNoRight(err):
                self.redirect(rgw_consts.Node_URLs.APP_ADM_LOGIN)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)


class AppSensorAdm(UIBase):
    def GetTitle(self):
        return "Sensor Adm"

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("AppSensorAdm", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = self.get_cookie(rgw_consts.Cookies.TENANT)
            if sid:
                await api_auth.CheckRight(sid)
                self.render(rgw_consts.Node_TPL_NAMES.APP_ADM_SENSOR,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            title=self.GetTitle(), sessionid=sid,
                            edit_url=rgw_consts.Node_URLs.APP_EDIT_SENSOR[1:])
            else:
                self.redirect(rgw_consts.Node_URLs.APP_ADM_LOGIN)
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            elif models.ErrorTypes.TypeOfNoRight(err):
                self.redirect(rgw_consts.Node_URLs.APP_ADM_LOGIN)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)


class AppEditSwitch(UIBase):
    def GetIconTbls(self):
        return [{'value': i, 'label': i.replace('_', ' ')} for i in rgw_consts.IconIds.SwitchIcons()]

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("AppEditSwitch", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = self.get_cookie(rgw_consts.Cookies.TENANT)
            if sid:
                await api_auth.CheckRight(sid)
                edit_mode = self.get_argument("edit_mode")
                if edit_mode == "edit":
                    rowid = self.get_argument("id")
                    self.render(rgw_consts.Node_TPL_NAMES.APP_EDIT_SWITCH,
                                app_js_dir=g_vars.g_cfg['web']['js_dir'],
                                app_css_dir=g_vars.g_cfg['web']['css_dir'],
                                app_template_dir=g_vars.g_cfg['web']['template_dir'],
                                title="Edit Switch", sessionid=sid,
                                id=rowid,
                                edit_mode=edit_mode,
                                iconid_tbls=self.GetIconTbls())
                else:
                    self.render(rgw_consts.Node_TPL_NAMES.APP_EDIT_SWITCH,
                                app_js_dir=g_vars.g_cfg['web']['js_dir'],
                                app_css_dir=g_vars.g_cfg['web']['css_dir'],
                                app_template_dir=g_vars.g_cfg['web']['template_dir'],
                                title="Add Switch", sessionid=sid,
                                id='',
                                edit_mode=edit_mode,
                                iconid_tbls=self.GetIconTbls())
            else:
                self.finish("please login")
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            elif models.ErrorTypes.TypeOfNoRight(err):
                self.redirect(rgw_consts.Node_URLs.APP_ADM_LOGIN)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)


class AppSwitchAdm(UIBase):
    def GetTitle(self):
        return "Switch Adm"

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("AppSwitchAdm", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = self.get_cookie(rgw_consts.Cookies.TENANT)
            if sid:
                await api_auth.CheckRight(sid)
                self.render(rgw_consts.Node_TPL_NAMES.APP_ADM_SWITCH,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            title=self.GetTitle(), sessionid=sid,
                            edit_url=rgw_consts.Node_URLs.APP_EDIT_SWITCH[1:])
            else:
                self.redirect(rgw_consts.Node_URLs.APP_ADM_LOGIN)
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            elif models.ErrorTypes.TypeOfNoRight(err):
                self.redirect(rgw_consts.Node_URLs.APP_ADM_LOGIN)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)


class AppEditSensorTrigger(UIBase):
    def GetLabelTbl(self):
        return {
            "en": {"sensor": "sensor", "switch": "switch",
                    'start_time': 'start', 'stop_time': 'stop',
                    'update_btn': 'update',
                    'remove_btn': 'remove',
                    'save_btn': 'save',
                    'check_interval': 'check interval(minute)',
                   'name': 'name'},

            "zh-cn": {"sensor": "传感器", "switch": "开关",
                    'start_time': '开始', 'stop_time': '结束',
                    'update_btn': '更新',
                    'remove_btn': '移除',
                    'save_btn': '保存',
                    'check_interval': '探测范围(XX分钟)',
                      'name': '名字'},

            "zh-tw": {"sensor": "傳感器", "switch": "開關",
                      'start_time': '開始', 'stop_time': '結束',
                      'update_btn': '更新',
                      'remove_btn': '移除',
                      'save_btn': '保存',
                      'check_interval': '探測範圍(XX分鐘)',
                      'name': '名字'}
        }

    def GetCheckIntervalTbls(self):
        return [{'value': i, 'label': str(i)} for i in (30, 60, 90, 120, 150, 180)]

    async def GetSensorTbls(self):
        sql_str = """select r1.id sensorid, r1.name sensor_name
                          from rgw_sensor r1
                          where r1.data_no<>? limit ?"""
        sql_args = (rgw_consts.SensorDataNo.SWITCH_ON_DURATION, rgw_consts.DbConsts.SEARCH_LIMIT)
        rows = await api_core.BizDB.Query([sql_str, sql_args])
        return [{'value': r['sensorid'], 'label': r['sensor_name']} for r in rows]

    async def GetSwitchTbls(self):
        sql_str = """select r1.id switchid, r1.name switch_name
                      from rgw_switch r1 limit ?"""
        sql_args = (rgw_consts.DbConsts.SEARCH_LIMIT,)
        rows = await api_core.BizDB.Query([sql_str, sql_args])
        return [{'value': r['switchid'], 'label': r['switch_name']} for r in rows]

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("AppEditSwitchActionTrigger", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = GetToken(self)
            ulang = GetLangCode(self)
            trigid = self.get_argument('triggerid', "0")
            if sid:
                await api_auth.CheckRight(sid)
                sensor_tbls = await self.GetSensorTbls()
                switch_tbls = await self.GetSwitchTbls()
                label_tbl = self.GetLabelTbl()[ulang]
                self.render(rgw_consts.Node_TPL_NAMES.APP_EDIT_SENSOR_TRIGGER,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            title="Set Trigger", sessionid=sid,
                            sensor_tbls=sensor_tbls,
                            switch_tbls=switch_tbls,
                            check_interval_tbls=self.GetCheckIntervalTbls(),
                            sensor_label=label_tbl['sensor'],
                            switch_label=label_tbl['switch'],
                            check_interval_label=label_tbl['check_interval'],
                            start_time_label=label_tbl['start_time'],
                            stop_time_label=label_tbl['stop_time'],
                            name_label=label_tbl['name'],
                            update_btn=label_tbl['update_btn'],
                            remove_btn=label_tbl['remove_btn'],
                            save_btn=label_tbl['save_btn'],
                            triggerid=trigid,
                            user_lang=ulang)
            else:
                self.finish("please login")
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            elif models.ErrorTypes.TypeOfNoRight(err):
                self.redirect(rgw_consts.Node_URLs.APP_ADM_LOGIN)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except cyclone_web.HTTPError:
            raise


class AppAdmSensorTrigger(UIBase):
    def GetTitle(self):
        return "Sensor Trigger Adm"

    def GetLabel(self):
        return {
            "en": {"remove": "remove", "refresh": "refresh", 'add': 'add', 'edit': 'edit'},
            "zh-cn": {"remove": "删除", "refresh": "刷新", 'add': "新增", 'edit': '编辑'},
            "zh-tw": {"remove": "刪除", "refresh": "刷新", 'add': "新增", 'edit': '編輯'}
        }

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("AppAdmSwitchActionTrigger", rg_lib.Cyclone.TryGetRealIp(self), 3)
            sid = GetToken(self)
            ulang = GetLangCode(self)
            label_tbl = self.GetLabel()
            if sid:
                await api_auth.CheckRight(sid)
                self.render(rgw_consts.Node_TPL_NAMES.APP_ADM_SENSOR_TRIGGER,
                            app_js_dir=g_vars.g_cfg['web']['js_dir'],
                            app_css_dir=g_vars.g_cfg['web']['css_dir'],
                            app_template_dir=g_vars.g_cfg['web']['template_dir'],
                            title=self.GetTitle(), sessionid=sid,
                            user_lang=ulang,
                            refresh_label=label_tbl[ulang]['refresh'],
                            add_label=label_tbl[ulang]['add'],
                            edit_label=label_tbl[ulang]['edit'],
                            remove_label=label_tbl[ulang]['remove'],
                            edit_action_url=rgw_consts.Node_URLs.APP_EDIT_SENSOR_TRIGGER[1:])
            else:
                login_url = DetectLoginPortal(self)
                self.redirect(login_url)
        except rg_lib.RGError as err:
            if models.ErrorTypes.TypeOfAccessOverLimit(err):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            elif models.ErrorTypes.TypeOfNoRight(err):
                self.redirect(rgw_consts.Node_URLs.APP_EM_LOGIN)
            else:
                self.finish(rgw_consts.WebContent.SERVER_ERROR)
        except cyclone_web.HTTPError:
            raise


class Logout(UIBase):
    async def __logout(self):
        sid = self.get_cookie(rgw_consts.Cookies.TENANT)
        if sid:
            await api_auth.Remove(sid)
        self.clear_cookie(rgw_consts.Cookies.TENANT)
        self.finish("<h2>you are now logged out</h2>")

    async def async_get(self):
        try:
            await api_req_limit.CheckMinuteRate("logout", rg_lib.Cyclone.TryGetRealIp(self), 3)
            await self.__logout()
        except rg_lib.RGError as err_obj:
            if models.ErrorTypes.TypeOfAccessOverLimit(err_obj):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)

    async def async_post(self):
        try:
            await api_req_limit.CheckMinuteRate("logout", rg_lib.Cyclone.TryGetRealIp(self), 3)
            await self.__logout()
        except rg_lib.RGError as err_obj:
            if models.ErrorTypes.TypeOfAccessOverLimit(err_obj):
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)

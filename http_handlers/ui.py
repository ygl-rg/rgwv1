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
import models
import settings


class UIBase(cyclone_web.RequestHandler):
    async def async_get(self):
        raise NotImplementedError()

    async def async_post(self):
        raise NotImplementedError()

    def get(self):
        return defer.ensureDeferred(self.async_get())

    def post(self):
        return defer.ensureDeferred(self.async_post())


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


async def CheckRight(req_handler):
    sid = GetToken(req_handler)
    return await api_auth.CheckRight(sid)


class AppAdmLogin(UIBase):
    def initialize(self, **kwargs):
        self.url_tbl = {'sensor': rgw_consts.URLs.APP_ADM_SENSOR,
                        'switch': rgw_consts.URLs.APP_ADM_SWITCH,
                        'zb_module': rgw_consts.URLs.APP_ADM_ZB_MODULE,
                        'zb_device': rgw_consts.URLs.APP_ADM_ZB_DEVICE,
                        'sys_cfg': rgw_consts.URLs.APP_SYS_CFG}

        self.adm_types = [{'name': 'Sensor/传感器', 'value': 'sensor'},
                          {'name': 'Switch/开关', 'value': 'switch', "checked": 1},
                          {'name': 'Zigbee Module', 'value': 'zb_module'},
                          {'name': 'Zigbee Device', 'value': 'zb_device'},
                          {'name': 'System Config/系统参数', 'value': 'sys_cfg'}]

    def RenderPage(self, user_lang, hint):
        self.render(rgw_consts.TPL_NAMES.APP_ADM_LOGIN,
                    app_js_dir=settings.WEB['js_dir'],
                    app_template_dir=settings.WEB['template_dir'],
                    title="rgw adm",
                    hint=hint,
                    loginurl=rgw_consts.URLs.APP_ADM_LOGIN,
                    bkgpng=settings.WEB['login_page_bkg'],
                    user_lang=user_lang,
                    adm_types=self.adm_types)

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            user_lang = GetLangCode(self)
            self.RenderPage(user_lang, '')
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

    async def async_post(self):
        await api_req_limit.CheckHTTP(self)
        pwd = self.get_argument('pwd', '').strip()
        adm_type = self.get_argument('adm_type', 'switch')
        user_lang = GetLangCode(self)
        if pwd:
            try:
                sessionid, expire_at, curr = await api_auth.Adm(pwd)
                self.set_cookie(rgw_consts.Cookies.TENANT, sessionid, expires=rg_lib.DateTime.ts2dt(expire_at),
                                httponly=True)
                if adm_type in self.url_tbl:
                    self.redirect(self.url_tbl[adm_type])
                else:
                    raise ValueError("adm type incorrect")
            except models.AccessOverLimit:
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            except models.PasswordError:
                self.RenderPage(user_lang, 'password error')
            except Exception:
                log.err()
                self.RenderPage(user_lang, 'server error')
        else:
            await self.async_get()


class AppLoginBase(UIBase):
    def RenderPage(self, hint_str):
        ulang = GetLangCode(self)
        app_opts = self.GetAppOptions()[ulang]
        self.render(rgw_consts.TPL_NAMES.APP_LOGIN,
                    app_js_dir=settings.WEB['js_dir'],
                    app_template_dir=settings.WEB['template_dir'],
                    title=self.GetTitle(),
                    hint=hint_str, loginurl=self.GetLoginUrl(), bkgpng=settings.WEB['login_page_bkg'],
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
        await api_req_limit.CheckHTTP(self)
        self.RenderPage("")

    async def async_post(self):
        await api_req_limit.CheckHTTP(self)
        pwd = self.get_argument('pwd', '').strip()
        ulang = self.get_argument('user_lang', 'en')
        if pwd:
            try:
                sessionid, expire_at, curr = await api_auth.Adm(pwd)
                self.set_cookie(rgw_consts.Cookies.TENANT, sessionid, expires=rg_lib.DateTime.ts2dt(expire_at),
                                httponly=True)
                self.set_cookie(rgw_consts.Cookies.USER_LANG, ulang, httponly=True)
                self.GotoPage()
            except models.PasswordError:
                self.RenderPage(models.MultiText.GetValue(multi_lang.password_error, ulang))
            except models.AccessOverLimit:
                self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
            except Exception:
                log.err()
                self.RenderPage(models.MultiText.GetValue(multi_lang.server_error, ulang))
        else:
            await self.async_get()


class EmLogin(AppLoginBase):
    def GetTitle(self):
        return "Elastic Monitoring"

    def GetLoginUrl(self):
        return rgw_consts.URLs.APP_EM_LOGIN

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
            self.redirect(rgw_consts.URLs.APP_EM)
        elif web_type == 'em_sensor':
            self.redirect(rgw_consts.URLs.APP_EM_SENSOR)
        else:
            raise cyclone_web.HTTPError(404)


class ViewSwitchSchedule(UIBase):
    def GetTitle(self):
        return "Switch Schedules"

    def GetLabel(self):
        return {
            "en": {"remove": "remove", 'valid': "valid schedules", 'invalid': 'overdue schedules',
                   'start_date': 'Start Date', 'stop_date': 'End Date', 'time': 'Time', 'working_duration': 'Working Duration',
                   'switches': 'Switches', 'next_schedule_time': 'Next Schedule Time',
                   'timezone': 'Timezone'},
            "zh-cn": {"remove": "删除", 'valid': "有效排程", 'invalid': "过期排程",
                      'start_date': '开始', 'stop_date': '结束', 'time': '时间',
                      'working_duration': '工作时长',
                      'switches': '开关', 'next_schedule_time': '下次排程',
                      'timezone': '时区'
                      },
            'zh-tw': {"remove": "移除", 'valid': "有效排程", 'invalid': "過期排程",
                      'start_date': '開始', 'stop_date': '結束', 'time': '時間',
                      'working_duration': '工作時長',
                      'switches': '開關', 'next_schedule_time': '下次排程',
                      'timezone': '時區'
                      }
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            label_tbl = self.GetLabel()[ulang]
            self.render(rgw_consts.TPL_NAMES.VIEW_SWITCH_SCHEDULES,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        sessionid=sid, user_lang=ulang,
                        label_tbl=label_tbl)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

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
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            temp_str = self.get_argument('sensorids')
            sensorids = c_escape.json_decode(c_escape.url_unescape(temp_str))
            if len(sensorids) < 1:
                raise cyclone_web.HTTPError(404, 'no sensor')
            sql_str = rg_lib.Sqlite.GenInSql("""select COALESCE(name,'') name, id from rgw_sensor where id in """,
                                             sensorids)
            sensors = await api_core.BizDB.Query([sql_str, sensorids])
            if len(sensors) > 0:
                self.render(rgw_consts.TPL_NAMES.VIEW_SENSOR_MINS_AVG_TREND,
                            app_js_dir=settings.WEB['js_dir'],
                            app_css_dir=settings.WEB['css_dir'],
                            app_template_dir=settings.WEB['template_dir'],
                            title=self.GetTitle(),
                            sessionid=sid, user_lang=ulang,
                            sensorids=sensorids,
                            mins_interval_tbls=self.GetMinsInterval())
            else:
                raise cyclone_web.HTTPError(404, 'no sensor')
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)

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
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            temp = self.get_argument('ids', '')
            sensorids = c_escape.json_decode(c_escape.url_unescape(temp))
            if len(sensorids) < 1:
                raise cyclone_web.HTTPError(404, 'no sensor')

            sql_str = rg_lib.Sqlite.GenInSql("""select COALESCE(name,'') name, id
                                                        from rgw_sensor where id in """,
                                             sensorids)
            sensors = await api_core.BizDB.Query([sql_str, sensorids])
            sensors_tbl = {i['id']: i for i in sensors}
            if len(sensors) > 0:
                self.render(rgw_consts.TPL_NAMES.VIEW_SENSOR_MINS_AVG_DATA,
                            app_js_dir=settings.WEB['js_dir'],
                            app_css_dir=settings.WEB['css_dir'],
                            app_template_dir=settings.WEB['template_dir'],
                            title=self.GetTitle(),
                            sessionid=sid, user_lang=ulang,
                            sensorids=sensorids,
                            sensors_tbl=sensors_tbl,
                            mins_interval_tbls=self.GetMinsInterval())
            else:
                raise cyclone_web.HTTPError(404, 'no sensor')
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

    async def async_get(self):
        return await self.handlePage_()


class ViewSwitchOnLogDetail(UIBase):
    def GetTitle(self):
        return "Switch On Duration Log Detail"

    def GetLabel(self):
        return {
            "en": {"monthly": "monthly", "range": "range", "query": "query",
                   'switch_on_duration': 'Switch On Duration', 'start': 'Start',
                   'stop': 'End', 'date': 'Date'},
            "zh-cn": {"monthly": "月份", "range": "范围", "query": "查询",
                      'switch_on_duration': '开启时长', 'start': '开始',
                      'stop': '结束', 'date': '日期'
                      },
            "zh-tw": {"monthly": "月份", "range": "范围", "query": "查詢",
                      'switch_on_duration': '開啟時長', 'start': '開始',
                      'stop': '結束', 'date': '日期'}
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            temp = self.get_argument('switchid', '')
            if len(temp) == 0:
                raise cyclone_web.HTTPError(404, 'no switch')
            row = await api_core.Switch.Get(["select id, name from rgw_switch where id=?", (temp,)])
            if row is None:
                raise cyclone_web.HTTPError(404, 'no switch')
            label_tbl = self.GetLabel()[ulang]
            self.render(rgw_consts.TPL_NAMES.VIEW_SWITCH_ON_LOG_DETAIL,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        sessionid=sid, user_lang=ulang,
                        switchid=temp,
                        switch_name=row.get('name', ''),
                        label_tbl=label_tbl)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

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
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            temp_str = self.get_argument('sensorids')
            sensorids = c_escape.json_decode(c_escape.url_unescape(temp_str))
            plotting_no = self.get_argument('plotting_no', '1')
            if len(sensorids) < 1:
                raise cyclone_web.HTTPError(404, 'no sensor')
            sql_str = rg_lib.Sqlite.GenInSql("""select COALESCE(name,'') name, id from rgw_sensor where id in """,
                                             sensorids)
            sensors = await api_core.BizDB.Query([sql_str, sensorids])
            if len(sensors) > 0:
                label_tbl = self.GetLabelTbl()[ulang]
                self.render(rgw_consts.TPL_NAMES.VIEW_SENSORS_RECENT_TREND,
                            app_js_dir=settings.WEB['js_dir'],
                            app_css_dir=settings.WEB['css_dir'],
                            app_template_dir=settings.WEB['template_dir'],
                            title=self.GetTitle(),
                            sessionid=sid, user_lang=ulang,
                            sensorids=sensorids,
                            hours_tbls=self.GetHoursTbls(),
                            mins_interval_tbls=self.GetMinsInterval(),
                            label_tbl=label_tbl,
                            plotting_no=plotting_no,
                            sensor_recent_hours_plotting_url=rgw_consts.URLs.VIEW_RECENT_HOURS_SENSOR_DATA_PLOTTING[
                                                             1:])
            else:
                raise cyclone_web.HTTPError(404, 'no sensor')
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

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
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            label_tbl = self.GetLabel()[ulang]
            self.render(rgw_consts.TPL_NAMES.VIEW_SWITCH_MONTHLY_USAGE,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        sessionid=sid, user_lang=ulang,
                        switch_on_detail_url=rgw_consts.URLs.VIEW_SWITCH_ON_LOG_DETAIL[1:],
                        label_tbl=label_tbl)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

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
                   'monthly_switch_usage_view': "switch monthly usage",
                   'goto': 'env data',
                   'name': 'Name', 'status': 'Status', 'remaining': 'Remaining'},
            "zh-cn": {"open": "打开", "close": "关闭", "open_duration_desc": "15-99999秒",
                      'set_schedule': "设置排程",
                      'switch_schedule_view': "查看排程",
                      'set_cond_action_view': '设置条件触发',
                      'monthly_switch_usage_view': "开关月统计",
                      'goto': '环境数据',
                      'name': '名字', 'status': '状态', 'remaining': '剩余开启时长'},
            "zh-tw": {"open": "打開", "close": "關閉", "open_duration_desc": "15-99999秒",
                      'set_schedule': "设置排程",
                      'switch_schedule_view': "查看排程",
                      'set_cond_action_view': '設置條件觸發',
                      'monthly_switch_usage_view': "開關月統計",
                      'goto': '環境數據',
                      'name': '名字', 'status': '狀態', 'remaining': '剩餘開啟時長'}
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            label_tbl = self.GetLabel()[ulang]
            self.render(rgw_consts.TPL_NAMES.APP_EM,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        sessionid=sid,
                        user_lang=ulang,
                        label_tbl=label_tbl,
                        switch_schedule_view_url=rgw_consts.URLs.VIEW_SWITCH_SCHEDULES[1:],
                        view_monthly_switch_usage_url=rgw_consts.URLs.VIEW_MONTHLY_SWITCH_USAGE[1:],
                        set_sensor_trigger_view_url=rgw_consts.URLs.APP_ADM_SENSOR_TRIGGER[1:],
                        em_sensor_url=rgw_consts.URLs.APP_EM_SENSOR[1:])
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

    async def async_get(self):
        return await self.handlePage_()


class AppEmSensor(UIBase):
    def GetTitle(self):
        return "Elastic Monitoring"

    def GetLabel(self):
        return {
            "en": {'history_trend_url': 'history trend',
                   'history_data_url': 'history data',
                   'goto': 'env ctrl', 'plot1': 'plot1', 'plot2': 'plot2',
                   'name': 'Name', 'status': 'Status', 'time': 'Time'},

            "zh-cn": {'history_trend_url': '历史趋势',
                      'history_data_url': '历史数据',
                      'goto': '环境控制', 'plot1': '趋势图1', 'plot2': '趋势图2',
                      'name': '名字', 'status': '状态', 'time': '时间'},
            "zh-tw": {'history_trend_url': '歷史趨勢',
                      'history_data_url': '歷史數據',
                      'goto': '环境控制', 'plot1': '趨勢图1', 'plot2': '趨勢图2',
                      'name': '名字', 'status': '狀態', 'time': '時間'}
        }

    async def handlePage_(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            label_tbl = self.GetLabel()[ulang]
            self.render(rgw_consts.TPL_NAMES.APP_EM_SENSOR,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        sessionid=sid, user_lang=ulang,
                        label_tbl=label_tbl,
                        sensor_mins_avg_trend_url=rgw_consts.URLs.VIEW_SENSOR_MINS_AVG_TREND[1:],
                        sensor_mins_avg_data_url=rgw_consts.URLs.VIEW_SENSOR_MINS_AVG_DATA[1:],
                        sensor_recent_hours_plotting_url=rgw_consts.URLs.VIEW_RECENT_HOURS_SENSOR_DATA_PLOTTING[1:],
                        sensor_recent_trend_url=rgw_consts.URLs.VIEW_SENSORS_RECENT_TREND[1:],
                        em_url=rgw_consts.URLs.APP_EM[1:],
                        goto_label=label_tbl['goto'],
                        plot1_label=label_tbl['plot1'],
                        plot2_label=label_tbl['plot2'],
                        history_trend_url_label=label_tbl['history_trend_url'],
                        history_data_url_label=label_tbl['history_data_url'])
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

    async def async_get(self):
        return await self.handlePage_()


class AppSysCfg(UIBase):
    def GetTimezoneOpts(self):
        import pytz
        asia_tzs = ['UTC'] + [i for i in pytz.common_timezones if i.find('Asia') >= 0]
        return [{'label': i, 'value': i} for i in asia_tzs]

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            self.render(rgw_consts.TPL_NAMES.APP_SYS_CFG,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        tz_options=self.GetTimezoneOpts(),
                        title="Sys Config", sessionid=sid)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppSysCfgMobile(UIBase):
    def GetTimezoneOpts(self):
        import pytz
        asia_tzs = ['UTC'] + [i for i in pytz.common_timezones if i.find('Asia') >= 0]
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
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            label_tbl = self.GetLabel()[ulang]
            self.render(rgw_consts.TPL_NAMES.APP_SYS_CFG_MOBILE,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        tz_options=self.GetTimezoneOpts(),
                        title="Sys Config", sessionid=sid,
                        label_tbl=label_tbl,
                        user_lang=ulang)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)


class AppEditSensor(UIBase):
    def GetDataNoTbls(self):
        return [{'value': i, 'label': i.replace('_', ' ')} for i in rgw_consts.SensorDataNo.LIST]

    def GetIconTbls(self):
        return [{'value': i, 'label': i.replace('_', ' ')} for i in rgw_consts.IconIds.SensorIcons()]

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            edit_mode = self.get_argument("edit_mode")
            if edit_mode == "edit":
                rowid = self.get_argument("id")
                self.render(rgw_consts.TPL_NAMES.APP_EDIT_SENSOR,
                            app_js_dir=settings.WEB['js_dir'],
                            app_css_dir=settings.WEB['css_dir'],
                            app_template_dir=settings.WEB['template_dir'],
                            title="Edit Sensor", sessionid=sid,
                            id=rowid, edit_mode=edit_mode,
                            data_no_tbls=self.GetDataNoTbls(),
                            iconid_tbls=self.GetIconTbls())
            else:
                self.render(rgw_consts.TPL_NAMES.APP_EDIT_SENSOR,
                            app_js_dir=settings.WEB['js_dir'],
                            app_css_dir=settings.WEB['css_dir'],
                            app_template_dir=settings.WEB['template_dir'],
                            title="Add Sensor", sessionid=sid,
                            id=0, edit_mode=edit_mode,
                            data_no_tbls=self.GetDataNoTbls(),
                            iconid_tbls=self.GetIconTbls())
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppSensorAdm(UIBase):
    def GetTitle(self):
        return "Sensor Adm"

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            self.render(rgw_consts.TPL_NAMES.APP_ADM_SENSOR,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(), sessionid=sid,
                        edit_url=rgw_consts.URLs.APP_EDIT_SENSOR[1:])
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppEditSwitch(UIBase):
    def GetIconTbls(self):
        return [{'value': i, 'label': i.replace('_', ' ')} for i in rgw_consts.IconIds.SwitchIcons()]

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            edit_mode = self.get_argument("edit_mode")
            if edit_mode == "edit":
                rowid = self.get_argument("id")
                self.render(rgw_consts.TPL_NAMES.APP_EDIT_SWITCH,
                            app_js_dir=settings.WEB['js_dir'],
                            app_css_dir=settings.WEB['css_dir'],
                            app_template_dir=settings.WEB['template_dir'],
                            title="Edit Switch", sessionid=sid,
                            id=rowid,
                            edit_mode=edit_mode,
                            iconid_tbls=self.GetIconTbls())
            else:
                self.render(rgw_consts.TPL_NAMES.APP_EDIT_SWITCH,
                            app_js_dir=settings.WEB['js_dir'],
                            app_css_dir=settings.WEB['css_dir'],
                            app_template_dir=settings.WEB['template_dir'],
                            title="Add Switch", sessionid=sid,
                            id='',
                            edit_mode=edit_mode,
                            iconid_tbls=self.GetIconTbls())
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppSwitchAdm(UIBase):
    def GetTitle(self):
        return "Switch Adm"

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            self.render(rgw_consts.TPL_NAMES.APP_ADM_SWITCH,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(), sessionid=sid,
                        edit_url=rgw_consts.URLs.APP_EDIT_SWITCH[1:])
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppZbModuleAdm(UIBase):
    def GetTitle(self):
        return "Zigbee Module Adm powered by RoundGIS Lab"

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            self.render(rgw_consts.TPL_NAMES.APP_ADM_ZB_MODULE,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        sync_zb_dev_url=rgw_consts.URLs.APP_SYNC_ZB_DEVICE[1:],
                        restore_module_url=rgw_consts.URLs.APP_RESTORE_ZB_MODULE[1:],
                        sessionid=sid)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppRestoreZbModule(UIBase):
    def GetTitle(self):
        return "Restore Zigbee Module powered by RoundGIS Lab"

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            moduleid = self.get_argument("moduleid")
            self.render(rgw_consts.TPL_NAMES.APP_RESTORE_ZB_MODULE,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        target_moduleid=moduleid,
                        sessionid=sid)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppEditZbDevice(UIBase):
    def GetDeviceNoTbls(self):
        return [{'label': i, 'value': i} for i in rgw_consts.XY_DeviceNo.LIST]

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            edit_mode = self.get_argument("edit_mode")
            if edit_mode == "edit":
                deviceid = self.get_argument("deviceid")
                self.render(rgw_consts.TPL_NAMES.APP_EDIT_ZB_DEVICE,
                            app_js_dir=settings.WEB['js_dir'],
                            app_css_dir=settings.WEB['css_dir'],
                            app_template_dir=settings.WEB['template_dir'],
                            title="Edit Zigbee Device",
                            edit_mode=edit_mode, deviceid=deviceid,
                            device_no_tbls=self.GetDeviceNoTbls(),
                            sessionid=sid)
            else:
                raise cyclone_web.HTTPError(404, "zigbee device edit mode incorrect")
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppZbDeviceAdm(UIBase):
    def GetTitle(self):
        return "Zigbee Device Adm powered by RoundGIS Lab"

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            self.render(rgw_consts.TPL_NAMES.APP_ADM_ZB_DEVICE,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        edit_zb_dev_url=rgw_consts.URLs.APP_EDIT_ZB_DEVICE[1:],
                        recap_zb_dev_url=rgw_consts.URLs.APP_RECAP_ZB_DEVICE[1:],
                        op_log_url=rgw_consts.URLs.APP_DEVICE_OP_LOG[1:],
                        op_error_count_url=rgw_consts.URLs.APP_DEVICE_OP_ERROR_COUNT[1:],
                        zb_module_adm_url=rgw_consts.URLs.APP_ADM_ZB_MODULE[1:],
                        sessionid=sid)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppSyncZbDevice(UIBase):
    def GetTitle(self):
        return "Sync Zigbee Device powered by RoundGIS Lab"

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            moduleid = self.get_argument("moduleid")
            self.render(rgw_consts.TPL_NAMES.APP_SYNC_ZB_DEVICE,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        moduleid=moduleid,
                        sessionid=sid)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppRecapZbDevice(UIBase):
    def GetTitle(self):
        return "Recap Zigbee Device powered by RoundGIS Lab"

    def GetDeviceNoTbls(self):
        return [{'label': i, 'value': i} for i in rgw_consts.XY_DeviceNo.LIST]

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            self.render(rgw_consts.TPL_NAMES.APP_RECAP_ZB_DEVICE,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(),
                        device_no_tbls=self.GetDeviceNoTbls(),
                        sessionid=sid)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppDeviceOpLog(UIBase):
    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            deviceid = self.get_argument("deviceid")
            self.render(rgw_consts.TPL_NAMES.APP_DEVICE_OP_LOG,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title="Device Op Log",
                        deviceid=deviceid,
                        sessionid=sid)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppDeviceOpErrorCount(UIBase):
    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            self.render(rgw_consts.TPL_NAMES.APP_DEVICE_OP_ERROR_COUNT,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title="Device Op Error Count",
                        op_log_url=rgw_consts.URLs.APP_DEVICE_OP_LOG[1:],
                        sessionid=sid)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_ADM_LOGIN)


class AppEditSensorTrigger(UIBase):
    def GetLabelTbl(self):
        return {
            "en": {"sensor": "sensor", "switch": "switch",
                   'start_time': 'start', 'stop_time': 'stop',
                   'update_btn': 'update condition',
                   'remove_btn': 'remove condition',
                   'save_btn': 'save',
                   'check_interval': 'check interval(minute)',
                   'name': 'name',
                   'message': 'message',
                   'no_condition_err': "error, no conditions",
                   'condition': 'condition'},

            "zh-cn": {"sensor": "传感器", "switch": "开关",
                      'start_time': '开始', 'stop_time': '结束',
                      'update_btn': '更新条件',
                      'remove_btn': '移除条件',
                      'save_btn': '保存',
                      'check_interval': '探测范围(XX分钟)',
                      'name': '名字',
                      'message': '消息',
                      'no_condition_err': "保存错误,没有条件",
                      'condition': '条件'},

            "zh-tw": {"sensor": "傳感器", "switch": "開關",
                      'start_time': '開始', 'stop_time': '結束',
                      'update_btn': '更新條件',
                      'remove_btn': '移除條件',
                      'save_btn': '保存',
                      'check_interval': '探測範圍(XX分鐘)',
                      'name': '名字',
                      'message': '訊息',
                      'no_condition_err': '保存錯誤，沒有條件',
                      'condition': '條件'}
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
        return [{'value': rgw_consts.PLACEHODER, 'label': '---------'}] + [{'value': r['switchid'], 'label': r['switch_name']} for r in rows]

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            trigid = self.get_argument('triggerid', "0")
            sensor_tbls = await self.GetSensorTbls()
            switch_tbls = await self.GetSwitchTbls()
            label_tbl = self.GetLabelTbl()[ulang]
            self.render(rgw_consts.TPL_NAMES.APP_EDIT_SENSOR_TRIGGER,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title="Set Trigger", sessionid=sid,
                        label_tbl=label_tbl,
                        sensor_tbls=sensor_tbls,
                        switch_tbls=switch_tbls,
                        check_interval_tbls=self.GetCheckIntervalTbls(),
                        triggerid=trigid,
                        user_lang=ulang)
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)


class AppAdmSensorTrigger(UIBase):
    def GetTitle(self):
        return "Sensor Trigger Adm"

    def GetLabel(self):
        return {
            "en": {"remove": "remove", "refresh": "refresh", 'add': 'add', 'edit': 'edit',
                   'name': 'name', 'start': 'start', 'stop': 'end'},
            "zh-cn": {"remove": "删除", "refresh": "刷新", 'add': "新增", 'edit': '编辑',
                      'name': '名字', 'start': '开始', 'stop': '结束'},
            "zh-tw": {"remove": "刪除", "refresh": "刷新", 'add': "新增", 'edit': '編輯',
                      'name': '名字', 'start': '開始', 'stop': '結束'}
        }

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            sid = await CheckRight(self)
            ulang = GetLangCode(self)
            label_tbl = self.GetLabel()
            self.render(rgw_consts.TPL_NAMES.APP_ADM_SENSOR_TRIGGER,
                        app_js_dir=settings.WEB['js_dir'],
                        app_css_dir=settings.WEB['css_dir'],
                        app_template_dir=settings.WEB['template_dir'],
                        title=self.GetTitle(), sessionid=sid,
                        user_lang=ulang,
                        label_tbl=label_tbl[ulang],
                        edit_action_url=rgw_consts.URLs.APP_EDIT_SENSOR_TRIGGER[1:])
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)


class Logout(UIBase):
    async def __logout(self):
        sid = self.get_cookie(rgw_consts.Cookies.TENANT)
        if sid:
            await api_auth.Remove(sid)
        self.clear_cookie(rgw_consts.Cookies.TENANT)
        self.finish("<h2>you are now logged out</h2>")

    async def async_get(self):
        try:
            await api_req_limit.CheckHTTP(self)
            await self.__logout()
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

    async def async_post(self):
        try:
            await api_req_limit.CheckHTTP(self)
            await self.__logout()
        except models.AccessOverLimit:
            self.finish(rgw_consts.WebContent.ACCESS_OVER_LIMIT)
        except models.NoRightError:
            self.redirect(rgw_consts.URLs.APP_EM_LOGIN)

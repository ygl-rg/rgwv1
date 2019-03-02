import os.path as os_path
import cyclone.web as cyclone_web
import rg_lib
from http_handlers import plotting as plotting_handlers, static_tpl as static_tpl_handlers, ui as ui_handlers, \
    internal_api as api_handlers
import rgw_consts
import settings


def GetStaticHandlers(static_path, export_path):
    return [(rg_lib.Cyclone.Dir2Url('imgs'), rg_lib.TempFileHandler, {"path": os_path.join(static_path, 'imgs')}),
            (rg_lib.Cyclone.Dir2Url('jslib'), rg_lib.TempFileHandler, {"path": os_path.join(static_path, 'jslib')}),
            (rg_lib.Cyclone.Dir2Url('js'), rg_lib.TempFileHandler, {"path": os_path.join(static_path, 'js')}),
            (rg_lib.Cyclone.Dir2Url('css'), rg_lib.TempFileHandler, {"path": os_path.join(static_path, 'css')}),
            (rg_lib.Cyclone.Dir2Url('export'), rg_lib.ExcelFileHandler, {"path": export_path})]


def GetStaticTplHandlers():
    return [
        (rg_lib.Cyclone.Dir2Url(settings.WEB['js_dir']), static_tpl_handlers.JsHandler),
        (rg_lib.Cyclone.Dir2Url(settings.WEB['css_dir']), static_tpl_handlers.CssHandler),
        (rg_lib.Cyclone.Dir2Url(settings.WEB['template_dir']), static_tpl_handlers.DojoTplHandler)
    ]


def GetApi():
    return [(rgw_consts.URLs.API_SYS_CFG, api_handlers.SysCfg),
            (rgw_consts.URLs.API_SENSOR_ADM, api_handlers.SensorAdm),
            (rgw_consts.URLs.API_SENSOR_TRIGGER, api_handlers.SensorTriggerAdm),
            (rgw_consts.URLs.API_SWITCH_ADM, api_handlers.SwitchAdm),
            (rgw_consts.URLs.API_EM, api_handlers.EnvMonitor),
            (rgw_consts.URLs.API_ZB_MODULE_ADM, api_handlers.ZbModuleAdm),
            (rgw_consts.URLs.API_ZB_DEVICE_ADM, api_handlers.ZbDeviceAdm)
            ]


def GetAPP():
    return [
        (rgw_consts.URLs.APP_ADM_LOGIN, ui_handlers.AppAdmLogin),
        (rgw_consts.URLs.APP_LOGOUT, ui_handlers.Logout),
        (rgw_consts.URLs.APP_SYS_CFG, ui_handlers.AppSysCfg),
        (rgw_consts.URLs.APP_SYS_CFG_MOBILE, ui_handlers.AppSysCfgMobile),
        (rgw_consts.URLs.APP_ADM_SENSOR, ui_handlers.AppSensorAdm),
        (rgw_consts.URLs.APP_EDIT_SENSOR, ui_handlers.AppEditSensor),
        (rgw_consts.URLs.APP_EDIT_SENSOR_TRIGGER, ui_handlers.AppEditSensorTrigger),
        (rgw_consts.URLs.APP_ADM_SENSOR_TRIGGER, ui_handlers.AppAdmSensorTrigger),
        (rgw_consts.URLs.APP_ADM_SWITCH, ui_handlers.AppSwitchAdm),
        (rgw_consts.URLs.APP_EDIT_SWITCH, ui_handlers.AppEditSwitch),
        (rgw_consts.URLs.APP_ADM_ZB_MODULE, ui_handlers.AppZbModuleAdm),
        (rgw_consts.URLs.APP_RESTORE_ZB_MODULE, ui_handlers.AppRestoreZbModule),
        (rgw_consts.URLs.APP_EDIT_ZB_DEVICE, ui_handlers.AppEditZbDevice),
        (rgw_consts.URLs.APP_ADM_ZB_DEVICE, ui_handlers.AppZbDeviceAdm),
        (rgw_consts.URLs.APP_SYNC_ZB_DEVICE, ui_handlers.AppSyncZbDevice),
        (rgw_consts.URLs.APP_RECAP_ZB_DEVICE, ui_handlers.AppRecapZbDevice),
        (rgw_consts.URLs.APP_DEVICE_OP_LOG, ui_handlers.AppDeviceOpLog),
        (rgw_consts.URLs.APP_DEVICE_OP_ERROR_COUNT, ui_handlers.AppDeviceOpErrorCount),
        (rgw_consts.URLs.APP_EM_LOGIN, ui_handlers.EmLogin),
        (rgw_consts.URLs.APP_EM, ui_handlers.AppEm),
        (rgw_consts.URLs.APP_EM_SENSOR, ui_handlers.AppEmSensor)
    ]


def GetViewHandlers():
    return [
        (rgw_consts.URLs.VIEW_SWITCH_SCHEDULES, ui_handlers.ViewSwitchSchedule),
        (rgw_consts.URLs.VIEW_RECENT_HOURS_SENSOR_DATA_PLOTTING, plotting_handlers.SensorHourlyLogHandler),
        (rgw_consts.URLs.VIEW_SENSOR_MINS_AVG_TREND, ui_handlers.ViewSensorMinsAvgTrend),
        (rgw_consts.URLs.VIEW_SENSOR_MINS_AVG_DATA, ui_handlers.ViewSensorMinsAvgData),
        (rgw_consts.URLs.VIEW_SWITCH_ON_LOG_DETAIL, ui_handlers.ViewSwitchOnLogDetail),
        (rgw_consts.URLs.VIEW_SENSORS_RECENT_TREND, ui_handlers.ViewSensorRecentTrend),
        (rgw_consts.URLs.VIEW_MONTHLY_SWITCH_USAGE, ui_handlers.ViewMonthlySwitchUsage)
    ]


class App(cyclone_web.Application):
    def __init__(self, static_path, export_path):
        handlers = GetStaticHandlers(static_path, export_path) + GetApi() + GetAPP() + GetViewHandlers() + GetStaticTplHandlers()
        cyclone_web.Application.__init__(self, handlers, gzip=True,
                                         template_path=os_path.join(settings.WEB['static_path'],
                                                                    settings.WEB['tpl_dir']))

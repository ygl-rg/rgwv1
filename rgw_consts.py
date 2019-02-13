# -*- coding: utf-8 -*-


class Timeout:
    COOKIE_INTERVAL = 3600*24*366


class DbConsts:
    SEARCH_LIMIT = 1024


class Cookies:
    TENANT = "nbgis1_"
    USER_LANG = "nbgislang_"


class SensorDataNo:
    TEMPERATURE = 'temperature'
    HUMIDITY = 'humidity'
    LIQUID_LEVEL = 'liquid_level'
    PH = 'pH'
    EC = 'ec'
    SWITCH_ON_DURATION = 'switch_on_duration'
    ILLUMINATION = 'illumination'
    MOISTURE = 'moisture'
    DISSOLVED_OXYGEN_LEVEL = 'dissolved_oxygen_level'
    CO2 = 'co2'
    LIST = [TEMPERATURE, HUMIDITY, LIQUID_LEVEL, PH, EC, ILLUMINATION, MOISTURE,
            SWITCH_ON_DURATION, DISSOLVED_OXYGEN_LEVEL, CO2]


class IconIds:
    AIR_CONDITIONER = "air_conditioner"
    AUTO_DRIP_IRRIGATION = "auto_drip_irrigation"
    AUTO_SPRINKLER_IRRIGATION = "auto_sprinkler_irrigation"
    VENTILATION_FAN = "ventilation_fan"
    EXHAUST_FAN = "exhaust_fan"
    LIGHT_UP = "light_up"
    WATER_PUMP = "water_pump"
    SPRAYER = "sprayer"
    AIR_TEMPERATURE = "air_temperature"
    AIR_HUMIDITY = "air_humidity"
    SOIL_TEMPERATURE = "soil_temperature"
    SOIL_MOISTURE = "soil_moisture"
    SOIL_EC = "soil_ec"
    CO2 = "CO2"
    O2 = "O2"
    WATER_LEVEL = "water_level"
    WATER_TEMPERATURE = "water_temperature"
    SUNSHINE = "sunshine"

    @classmethod
    def SwitchIcons(cls):
        return [cls.AIR_CONDITIONER, cls.AUTO_DRIP_IRRIGATION, cls.AUTO_SPRINKLER_IRRIGATION,
                cls.VENTILATION_FAN, cls.EXHAUST_FAN, cls.LIGHT_UP, cls.WATER_PUMP,
                cls.SPRAYER]

    @classmethod
    def SensorIcons(cls):
        return [cls.AIR_TEMPERATURE, cls.AIR_HUMIDITY, cls.SOIL_TEMPERATURE, cls.SOIL_MOISTURE,
                cls.SOIL_EC, cls.CO2, cls.O2, cls.WATER_LEVEL, cls.WATER_TEMPERATURE, cls.SUNSHINE]


class XY_DeviceNo:
    XY_SWITCH = 'XY_SWITCH'
    XY_TEMP_HUMIDITY_SENSOR = 'XY_TEMPERATURE_HUMIDITY_SENSOR'
    XY_ILLUMINATION_SENSOR = 'XY_ILLUMINATION_SENSOR'
    XY_LIQUID_LEVEL_SENSOR = 'XY_LIQUID_LEVEL_SENSOR'
    XY_SOIL_3IN1_SENSOR = 'XY_SOIL_3IN1_SENSOR'
    XY_CO2_SENSOR = 'XY_CO2_SENSOR'


class Node_URLs:
    APP_LOGOUT = r"logout"
    APP_ADM_LOGIN = r"adm/login"
    APP_EM_LOGIN = r"login"
    APP_EDIT_SENSOR_TRIGGER = r"edit/sensortrigger"
    APP_ADM_SENSOR_TRIGGER = r"adm/sensortrigger"
    VIEW_SWITCH_SCHEDULES = r"v/ss"
    VIEW_SWITCH_ON_LOG_DETAIL = r'v/sold'
    VIEW_SENSOR_MINS_AVG_TREND = r"v/smat"
    VIEW_SENSOR_MINS_AVG_DATA = r"v/smad"
    VIEW_RECENT_HOURS_SENSOR_DATA_PLOTTING = r'v/rhsdp'
    VIEW_SENSORS_RECENT_TREND = r'v/srt'
    VIEW_EM_SENSOR = r"v/emsensor"
    VIEW_MONTHLY_SWITCH_USAGE = r'v/msu'
    APP_EM = r"em"
    APP_EM_SENSOR = r"em/sensor"
    APP_SYS_CFG = r'cfg/sys'
    APP_SYS_CFG_MOBILE = r'cfg/sys/m'
    APP_EDIT_SENSOR = r"edit/sensor"
    APP_ADM_SENSOR = r"adm/sensor"
    APP_EDIT_SWITCH = r"edit/switch"
    APP_ADM_SWITCH = r"adm/switch"
    API_EM = r"api/em"
    API_SYS_CFG = r'api/syscfg'
    API_SENSOR_ADM = r'api/sensoradm'
    API_SENSOR_TRIGGER = r"api/sensortrigger"
    API_SWITCH_ADM = r'api/switchadm'
    EXPORT_FMT = "export/{0}"


class Node_TPL_NAMES:
    APP_LOGIN = r"app_login_tpl.html"
    APP_ADM_LOGIN = r"app_adm_login_tpl.html"
    APP_EDIT_USER = r"app_edit_user_tpl.html"
    APP_ADM_USER = r"app_adm_user_tpl.html"
    VIEW_SWITCH_SCHEDULES = r"view_switch_schedules_tpl.html"
    VIEW_SWITCH_ON_LOG_DETAIL = r"view_switch_on_log_detail_tpl.html"
    VIEW_SENSOR_MINS_AVG_TREND = r'view_sensors_mins_avg_trend_tpl.html'
    VIEW_SENSOR_MINS_AVG_DATA = r'view_sensors_mins_avg_data_tpl.html'
    VIEW_SENSORS_RECENT_TREND = r'view_sensors_recent_trend2_tpl.html'
    VIEW_SWITCH_MONTHLY_USAGE = r"view_monthly_switch_usage_tpl.html"
    APP_EM = r"app_em_tpl.html"
    APP_EM_MOBILE = r"app_em_mobile_tpl.html"
    APP_EM_SENSOR = r"app_em_sensor2_tpl.html"
    APP_EM_SENSOR_MOBILE = r"app_em_sensor_mobile_tpl.html"
    APP_SYS_CFG = r'app_sys_cfg_tpl.html'
    APP_SYS_CFG_MOBILE = r'app_sys_cfg2_tpl.html'
    APP_EDIT_SENSOR = r'app_edit_sensor_tpl.html'
    APP_ADM_SENSOR = r'app_adm_sensor_tpl.html'
    APP_EDIT_SENSOR_TRIGGER = r"app_edit_sensor_trigger_tpl.html"
    APP_ADM_SENSOR_TRIGGER = r"app_adm_sensor_trigger_tpl.html"
    APP_EDIT_SWITCH = r'app_edit_switch_tpl.html'
    APP_ADM_SWITCH = r'app_adm_switch_tpl.html'


class Keys:
    MINUTE_RATE_FMT = "access_minute_rate:{0}_{1}_{2}" #prefix,key &ip
    USER_SESSION = 'user_session:{0}'
    SENSOR_TRIGGER_INTERVAL = 'sensor_trigger_interval:{0}'  # action rowid
    DEVICE_OP_COUNT = "device_op_count:{0}" # switchid


class WebContent:
    ACCESS_OVER_LIMIT = "<h2>access over limit</h2>"
    SERVER_ERROR = "<h2>server error</h2>"
    PLEASE_LOGIN = "<h2>please login</h2>"
    PWD_ERR = "<h2>invalid password</h2>"


class Network:
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


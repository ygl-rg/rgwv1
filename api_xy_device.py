from twisted.python import log
import api_core
import api_rxg
import rg_lib
import models
import rgw_consts


async def SyncSensor():
    devs = await api_rxg.EM.ListDevice('sensor')
    sensors = []
    temp = [d for d in devs if d['device_no'] == rgw_consts.XY_DeviceNo.XY_TEMP_HUMIDITY_SENSOR]
    GenTemperatureHumidity(sensors, temp)
    temp = [d for d in devs if d['device_no'] == rgw_consts.XY_DeviceNo.XY_SOIL_3IN1_SENSOR]
    GenSoil3In1(sensors, temp)
    temp = [d for d in devs if d['device_no'] == rgw_consts.XY_DeviceNo.XY_LIQUID_LEVEL_SENSOR]
    GenLiquidLevel(sensors, temp)
    temp = [d for d in devs if d['device_no'] == rgw_consts.XY_DeviceNo.XY_ILLUMINATION_SENSOR]
    GenIllumination(sensors, temp)
    temp = [d for d in devs if d['device_no'] == rgw_consts.XY_DeviceNo.XY_CO2_SENSOR]
    GenCO2(sensors, temp)
    sql_rows = []
    sql_rows.extend([models.Sensor.DynInsert(s, True) for s in sensors])
    sql_str = rg_lib.Sqlite.GenInSql("delete from rgw_sensor where deviceid not in ",
                                     devs)
    sql_args = [d['id'] for d in devs]
    sql_rows.append([sql_str, sql_args])
    await api_core.BizDB.Interaction(sql_rows)


async def SyncSwitch():
    devs = await api_rxg.EM.ListDevice('switch')
    switches = []
    GenSwitch(switches, devs)
    sql_rows = []
    sql_rows.extend([models.Switch.DynInsert(s, True) for s in switches])
    sql_str = rg_lib.Sqlite.GenInSql("delete from rgw_switch where id not in ",
                                     devs)
    sql_args = [d['id'] for d in devs]
    sql_rows.append([sql_str, sql_args])
    await api_core.BizDB.Interaction(sql_rows)


def GenSwitch(switches, devices):
    for dev in devices:
        s1 = models.Switch.make(dev['id'], '{0} switch'.format(dev['id']))
        s1['iconid'] = rgw_consts.IconIds.LIGHT_UP
        switches.append(s1)


def GenTemperatureHumidity(sensors, devices):
    for dev in devices:
        s1 = models.Sensor.make(dev['id'], 0, rgw_consts.SensorDataNo.TEMPERATURE,
                                '{0} temperature'.format(dev['id']))
        s1['val_unit'] = 'C'
        s1['iconid'] = rgw_consts.IconIds.AIR_TEMPERATURE
        s2 = models.Sensor.make(dev['id'], 1, rgw_consts.SensorDataNo.HUMIDITY,
                                '{0} humidity'.format(dev['id']))
        s2['val_unit'] = '%'
        s2['iconid'] = rgw_consts.IconIds.AIR_HUMIDITY
        sensors.append(s1)
        sensors.append(s2)


def GenSoil3In1(sensors, devices):
    for dev in devices:
        s1 = models.Sensor.make(dev['id'], 0, rgw_consts.SensorDataNo.MOISTURE,
                                '{0} moisture'.format(dev['id']))
        s1['val_unit'] = '%'
        s1['iconid'] = rgw_consts.IconIds.SOIL_MOISTURE
        s2 = models.Sensor.make(dev['id'], 1, rgw_consts.SensorDataNo.TEMPERATURE,
                                '{0} temperature'.format(dev['id']))
        s2['val_unit'] = 'C'
        s2['iconid'] = rgw_consts.IconIds.SOIL_TEMPERATURE
        s3 = models.Sensor.make(dev['id'], 2, rgw_consts.SensorDataNo.EC,
                                '{0} ec'.format(dev['id']))
        s3['val_unit'] = 'uS/cm'
        s3['iconid'] = rgw_consts.IconIds.SOIL_EC
        sensors.append(s1)
        sensors.append(s2)
        sensors.append(s3)


def GenLiquidLevel(sensors, devices):
    for dev in devices:
        s1 = models.Sensor.make(dev['id'], 0, rgw_consts.SensorDataNo.LIQUID_LEVEL,
                                '{0} liquid level'.format(dev['id']))
        s1['val_unit'] = 'm'
        s1['iconid'] = rgw_consts.IconIds.WATER_LEVEL
        sensors.append(s1)


def GenIllumination(sensors, devices):
    for dev in devices:
        s1 = models.Sensor.make(dev['id'], 0, rgw_consts.SensorDataNo.ILLUMINATION,
                                '{0} illumination'.format(dev['id']))
        s1['val_unit'] = '%'
        s1['iconid'] = rgw_consts.IconIds.SUNSHINE
        s1['func_body'] = """
               local i1 = tonumber(ARGV[1]);
               local MAX_VOLT = 0x1A;
               if i1 > MAX_VOLT then
                   i1 = MAX_VOLT;
               end
               return tostring(100*i1/MAX_VOLT);
        """
        sensors.append(s1)


def GenCO2(sensors, devices):
    """
    max volt is 2.6V
    :param sensors:
    :param devices:
    :return:
    """
    for dev in devices:
        s1 = models.Sensor.make(dev['id'], 0, rgw_consts.SensorDataNo.CO2,
                                '{0} co2'.format(dev['id']))
        s1['val_unit'] = '%'
        s1['iconid'] = rgw_consts.IconIds.CO2
        s1['func_body'] = """
               local i1 = tonumber(ARGV[1]);
               local MAX_VOLT = 0x1A;
               if i1 > MAX_VOLT then
                   i1 = MAX_VOLT;
               end
               return tostring(100*i1/MAX_VOLT);
        """
        sensors.append(s1)


async def ProbeAndSync():
    modules = await api_rxg.ZbModule.ListModule('active')
    devs = []
    for module in modules:
        result = await api_rxg.ZbModule.ProbeDevice(module['id'])
        log.msg(result)
        if len(result['devices']) > 0:
            await SyncSensor()
            await SyncSwitch()
            devs.extend(result['devices'])
    return devs

from twisted.python import log
import rg_lib
import rgw_consts
import api_core
import api_sensor_data
import api_switch_action
import api_rxg
import models


def ListSensor():
    sql_str = """select r1.id id, 
                        r1.extra_arg0 extra_arg0,
                        r1.deviceid deviceid,
                        r1.val_offset val_offset,
                        r1.data_no data_no,
                         COALESCE(r1.func_body,'') func_body
                  from rgw_sensor r1"""
    return api_core.BizDB.Query([sql_str, []])


async def ScanSensor():
    try:
        ready_sensors = []
        sensors = await ListSensor()
        sensorids = [s['id'] for s in sensors]
        devs = await api_rxg.EM.GetSensorVal(sensorids)
        curr_ts = rg_lib.DateTime.ts()
        dev_tbl = {i['id']: i for i in devs}
        for sensor in sensors:
            if sensor['deviceid'] in dev_tbl:
                dev = dev_tbl[sensor['deviceid']]
                if len(dev['vals']) > sensor['val_offset']:
                    sensor['val'] = dev['vals'][sensor['val_offset']]
                    sensor['uts'] = curr_ts
                    if models.Sensor.HasFuncBody(sensor):
                        argv = [sensor['val'], sensor['extra_arg0']] if models.Sensor.HasExtraArg0(sensor) else [
                            sensor['val']]
                        bytes_obj = await rg_lib.TxRedis.Eval(api_core.BizDB.redis_conn,
                                                              sensor['func_body'],
                                                              args=argv)
                        if bytes_obj:
                            sensor['val'] = float(bytes_obj)
                    ready_sensors.append(sensor)
        if len(ready_sensors) > 0:
            await api_core.Sensor.UpdateVal(ready_sensors)
            sensor_data_list = [models.SensorData.Sync(s) for s in ready_sensors]
            await api_sensor_data.Add(sensor_data_list)
        await HandleSensorTrigger()
    except Exception as e:
        log.err()


async def HandleSensorTrigger():
    curr_ts = rg_lib.DateTime.ts()
    sql_str = """select * from rgw_sensor_trigger
                  where ((start_ts=0 and stop_ts=0) or 
                        (start_ts>0 and stop_ts=0 and start_ts<?) or
                        (start_ts=0 and stop_ts>0 and stop_ts>?) or
                        (start_ts>0 and stop_ts>0 and start_ts<? and stop_ts>?))"""

    sql_args = [curr_ts, curr_ts, curr_ts, curr_ts]
    rows = await api_core.SensorTrigger.Query([sql_str, sql_args])
    if len(rows) > 0:
        for row in rows:
            await __HandleTriggerHelper(curr_ts, row)


async def __HandleTriggerHelper(ts, trigger_mdl):
    sensor_infos = await api_core.BizDB.Query(["""select sensorid, op,rval 
                                               from rgw_sensor_trigger_sensor
                                               where triggerid=?""",
                                               (trigger_mdl['id'],)])
    if len(sensor_infos) < 1:
        return False
    expr_args = []
    for s in sensor_infos:
        row = await api_sensor_data.GetLatestAvg(s['sensorid'])
        if row:
            expr_args.append((s['op'], row['avg_val'], s['rval']))
    if len(expr_args) == len(sensor_infos):
        sql, sql_args = models.SensorTrigger.GenAndExpr(expr_args)
        res = api_core.SensorTrigger.Eval(sql, sql_args)
        if res > 0:
            has_valid_interval = await api_core.SensorTrigger.InCheckInterval(trigger_mdl['id'])
            if not has_valid_interval:
                switch_infos = await api_core.SensorTrigger.Query(["""select * from rgw_sensor_trigger_switch
                                                                  where triggerid=?""", (trigger_mdl['id'],)])
                on_switches = [s for s in switch_infos if s['switchid'] != rgw_consts.PLACEHODER and s['action_no'] == 'ON']
                off_switchids = [s['switchid'] for s in switch_infos if s['switchid'] != rgw_consts.PLACEHODER and s['action_no'] == 'OFF']
                if len(on_switches) > 0:
                    await api_switch_action.Open2({s['switchid']: s['working_seconds'] for s in on_switches},
                                                  rg_lib.DateTime.utc())
                if len(off_switchids) > 0:
                    await api_switch_action.Close(off_switchids)
                if len(trigger_mdl['message']) > 0:
                    await api_core.TriggerLog.Add(models.TriggerLog.make(ts, trigger_mdl['id'],
                                                                         trigger_mdl['message']))
                await SendEmail(trigger_mdl)
                await api_core.SensorTrigger.SetCheckInterval(trigger_mdl)


async def ScanSwitch():
    try:
        await api_switch_action.AutoSync()
    except Exception as e:
        log.err()


async def SendEmail(trigger_mdl):
    tbl = await api_core.SysCfg.GetElasticEmailInfo()
    if tbl and len(trigger_mdl['emails']) > 0 and len(trigger_mdl['message']) > 0:
        await api_core.ElasticEmail.SendEmail(tbl['url'],
                                              tbl['api_key'],
                                              tbl['sender'],
                                              trigger_mdl['emails'],
                                              trigger_mdl['message'],
                                              trigger_mdl['message'], 10)

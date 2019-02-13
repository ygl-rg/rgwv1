# elastic monitoring api
from twisted.python import log
import collections
import os.path as os_path
import bson
from twisted.internet import threads
import rg_lib
import g_vars
import rgw_consts
import node_models as models
import sensor_log_report
import monthly_switch_usage_report
import api_core
import api_sensor_avg_data
import api_switch_action
import api_switch_schedule
import api_switch_stats


async def __AddSchedule(schedule_arg):
    """
    :param schedule_arg: {"switchids", "working_seconds", other fields}
    :return: {"switchids:[,...,...]}
    """
    res = {'switchids': [], 'data_tbl': collections.defaultdict(list)}
    tz_obj = await api_core.SysCfg.GetTimezone()
    schedule_mdl = models.SwitchSchedule.make(models.SwitchSchedule.GenId(), "ON",
                                              schedule_arg['switchids'],
                                              schedule_arg['local_start_time'],
                                              schedule_arg['local_stop_time'],
                                              schedule_arg['hour'],
                                              schedule_arg['minute'],
                                              schedule_arg['second'],
                                              tz_obj.zone,
                                              schedule_arg['working_seconds'])
    check_res = await api_switch_schedule.CheckConflict(schedule_mdl)
    if len(check_res['switchids']) < 1:
        await api_switch_schedule.Add(schedule_mdl)
    else:
        res['switchids'].extend(check_res['switchids'])
        for rowid in check_res['switchids']:
            res['data_tbl'][rowid].extend(check_res['data_tbl'][rowid])
    return res


async def GetSwitch(arg):
    """
    :param arg: {}
    :return: {"switches": [switch mdl,...]}
    """
    if "switchids" in arg:
        sql_str = rg_lib.Sqlite.GenInClause("select id, name, iconid, tag, uts from rgw_switch where id in ",
                                            arg['switchids'])
        sql_args = arg['switchids']
    else:
        sql_str = "select id, name, iconid, tag, uts from rgw_switch"
        sql_args = []
    switches = await api_core.BizDB.Query([sql_str, sql_args])
    curr = rg_lib.DateTime.ts()
    for s in switches:
        if (s['uts'] is None) or s['uts'] < (curr - 90):
            s['status'] = rgw_consts.Network.OFFLINE
        else:
            action = await api_switch_action.GetSuccOn(s['id'])
            if action:
                s['status'] = models.Switch.ON
                s['remaining_seconds'] = action['remaining_seconds']
            else:
                s['status'] = models.Switch.OFF
    return switches


async def OpenSwitch(para):
    """
    :param para: {"switchids", "working_seconds": 0}
    :return:
    """
    if para['working_seconds'] < 15:
        raise rg_lib.RGError(rg_lib.ErrorType.ServerErr('working seconds >= 15 '))
    await api_switch_action.Open(para['switchids'], rg_lib.DateTime.utc(),
                                 para['working_seconds'])
    return "ok"


async def CloseSwitch(switchids):
    """
    :param deviceids: list of device ids
    :return:
    """
    await api_switch_action.Close(switchids)
    return "ok"


def AddSchedule(para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"schedule": schedule tbl}
    :return:
    """
    temp = para['schedule']
    temp['second'] = 0
    return __AddSchedule(temp)


async def RemoveSchedule(para):
    """
    :param para: {"scheduleids": [id,...]}
    :return:
    """
    sql_rows = []
    for sid in para['scheduleids']:
        sql_rows.append(["delete from rgw_switch_schedule_switch where scheduleid=?", (sid,)])
        sql_rows.append(["delete from rgw_switch_schedule where id=?", (sid,)])
    await api_switch_schedule.Remove(sql_rows)
    return "ok"


async def GetUserSchedules(para):
    """
    :param para: {'search_no': }
    :return: [schedule obj,...]
    """
    search_no = para.get('search_no', 'all')
    if search_no == 'all':
        sql_str = """select r1.* from rgw_switch_schedule r1"""
        sql_args = []
    elif search_no == 'valid':
        sql_str = """select r1.* from rgw_switch_schedule r1 where r1.next_run_ts is not null"""
        sql_args = []
    elif search_no == 'invalid':
        sql_str = """select r1.* from rgw_switch_schedule r1 where r1.next_run_ts is null"""
        sql_args = []
    else:
        raise rg_lib.RGError(models.ErrorTypes.UnsupportedOp())
    return await api_switch_schedule.QueryMdl([sql_str, sql_args])


async def GetSensor(para):
    """
    :param para: {sensorids (optional)}
    :return: sensors
    """
    if "sensorids" in para:
        sql_str = rg_lib.Sqlite.GenInClause("""select * from rgw_sensor where id in """,
                                            para['sensorids'])
    else:
        sql_str = """select * from rgw_sensor"""
    return await api_core.Sensor.Query([sql_str, []])


async def FindSensorMinsAvgLog(para):
    """
    :param para: {"sensorids":[], "start_ts": timestamp, "stop_ts": timestamp,
                  "mins_interval": integer}
                  or {"sensorids":[], "hours": hours range, "mins_interval": integer}
    :return: {"sensorids":[], "log_tbl": {sensorid->[mins data,...]},
              "sensors_tbl": {sensorid->sensor tbl}, "ts_series": [series of timestamp]}
    """
    if 'start_ts' in para and 'stop_ts' in para:
        start_ts, stop_ts = para['start_ts'], para['stop_ts']
    elif 'hours' in para:
        stop_ts = rg_lib.DateTime.dt2ts(rg_lib.DateTime.utc())
        start_ts = stop_ts - para['hours'] * 3600
    else:
        raise rg_lib.RGError(models.ErrorTypes.UnsupportedOp())

    # for start_ts to align %HH:00:00
    start_ts = rg_lib.DateTime.dt2ts(rg_lib.DateTime.ts2dt(start_ts).replace(minute=0, second=0))
    tbls = await api_sensor_avg_data.QueryMinAvg(start_ts, stop_ts, para['sensorids'],
                                                 para['mins_interval'], 2000)
    result = {"sensorids": para['sensorids'], "log_tbl": collections.defaultdict(list),
              'ts_series': rg_lib.DateTime.GetMinSeries(start_ts, stop_ts, para['mins_interval'], 'ts')}
    sql_str = rg_lib.Sqlite.GenInSql("""select r1.id,
                                               r1.data_no,
                                               r1.name, 
                                               r1.val_unit,
                                               r1.val_precision
                                        from rgw_sensor r1 where r1.id in """,
                                     para['sensorids'])
    tbls2 = await api_core.Sensor.Query([sql_str, para['sensorids']])
    for tbl in tbls:
        result['log_tbl'][str(tbl['sensorid'])].append(tbl)
    result['sensors_tbl'] = {str(t['id']): t for t in tbls2}
    return result


async def FindSensorMinsAvgLog2(para):
    """
    log_tbl is sorted by cts
    :param para: {"sensorids":[], "start_ts": timestamp, "stop_ts": timestamp,
                  "mins_interval": integer}
                  or {"sensorids":[], "hours": hours range, "mins_interval": integer}
    :return: {"sensorids":[], "log_tbl": {sensorid->{cts: record,}},
              "sensors_tbl": {sensorid->sensor tbl}, "ts_series": [series of timestamp]}
    """
    result = await FindSensorMinsAvgLog(para)
    temp = {}
    for sensorid_str in result['log_tbl']:
        data_list = result['log_tbl'][sensorid_str]
        if sensorid_str not in temp:
            temp[sensorid_str] = collections.OrderedDict()
        for rec in data_list:
            temp[sensorid_str][rec['cts']] = rec
    result['log_tbl'] = temp
    return result


def ExportSensorMinsAvgLog(para):
    """
    :param para: {"sensorids":[], "start_ts": timestamp, "stop_ts": timestamp,
                  "mins_interval": integer}
                  or {"sensorids":[], "hours": hours range, "mins_interval": integer,
                  }
    :return: URL
    """
    return __GenSensorMinsAvgLog(para, 'url')


async def __GenSensorMinsAvgLog(para, result_no):
    """
    :param para: {"sensorids":[], "start_ts": timestamp, "stop_ts": timestamp,
                  "mins_interval": integer, 'tz_offset': integer}
                  or {"sensorids":[], "hours": hours range, "mins_interval": integer,
                  'tz_offset': integer}
    :param result_no: url or bytes
    :return: {"url" or "bytes"}
    """
    from io import BytesIO
    result = {}
    log_tbl = await FindSensorMinsAvgLog2(para)
    tz_obj = await api_core.SysCfg.GetTimezone()
    log_tbl['tz_offset'] = tz_obj.utcoffset(rg_lib.DateTime.utc()).total_seconds()
    if result_no == 'url':
        file_name = "{0}.xlsx".format(bson.ObjectId())
        file_path = os_path.join(g_vars.g_cfg['web']['export_path'], file_name)
        await threads.deferToThread(sensor_log_report.Make, file_path, log_tbl)
        result['url'] = os_path.join('/', rgw_consts.Node_URLs.EXPORT_FMT.format(file_name))
    else:
        io_obj = BytesIO()
        await threads.deferToThread(sensor_log_report.Make, io_obj, log_tbl)
        io_obj.seek(0)
        result['bytes'] = bson.Binary(io_obj.read())
        io_obj.close()
    return result


async def GetSwitchOnDetail(para):
    """
    :param para: {"switchid": switchid, "start_ts": timestamp,
                  "stop_ts": timestamp, "search_no": "range" or "monthly",
                  "year": year, "month": month}
    :return: {"recs": [], 'total_val': xx}
    """
    tz_obj = await api_core.SysCfg.GetTimezone()
    if para['search_no'] == 'range':
        log_tbl = await api_switch_stats.GetDetail(para['switchid'], para['start_ts'], para['stop_ts'])
    else:
        usages = await api_switch_stats.GetMonthlyUsage(para['year'], para['month'], para['switchid'],
                                                        tz_obj)
        log_tbl = {'recs': usages}
        log_tbl['total_val'] = sum([rec['val'] for rec in log_tbl['recs']])
    return log_tbl


async def ListSwitchMonthlyUsage(para):
    """
    :param para: {year, month}
    :return: {"switches": [switch modls], "rec_tbl": {switchid:[SwitchOpDuration,...]}}
    """
    tz_obj = await api_core.SysCfg.GetTimezone()
    switches = await api_core.Switch.Query(["select id, name from rgw_switch", []])
    result = {'switches': switches, 'rec_tbl': {}}
    for i in switches:
        usages = await api_switch_stats.GetMonthlyUsage(para['year'], para['month'], i['id'],
                                                        tz_obj)
        result['rec_tbl'][i['id']] = usages
    return result


def ExportSwitchMonthlyUsage(para):
    """
    :param para: {year, month}
    :return: URL
    """
    return __GenSwitchMonthlyUsage(para, 'url')


async def __GenSwitchMonthlyUsage(para, result_no):
    """
    :param para:
    :param result_no: url or bytes
    :return: {"url" or "bytes"}
    """
    from io import BytesIO
    result = {}
    arg = await ListSwitchMonthlyUsage(para)
    arg['year'], arg['month'] = para['year'], para['month']
    if result_no == 'url':
        file_name = "{0}.xlsx".format(bson.ObjectId())
        file_path = os_path.join(g_vars.g_cfg['web']['export_path'], file_name)
        await threads.deferToThread(monthly_switch_usage_report.Make, file_path, arg)
        result['url'] = os_path.join('/', rgw_consts.Node_URLs.EXPORT_FMT.format(file_name))
    else:
        io_obj = BytesIO()
        await threads.deferToThread(monthly_switch_usage_report.Make, io_obj, arg)
        io_obj.seek(0)
        result['bytes'] = bson.Binary(io_obj.read())
        io_obj.close()
    return result



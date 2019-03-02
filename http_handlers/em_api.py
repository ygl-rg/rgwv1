from twisted.python import log
from twisted.internet import threads
import bson
from os import path as os_path
import collections
import rg_lib
import rgw_consts
import models
import api_core
import api_req_limit
import api_auth
import api_switch_action
import api_switch_schedule
import api_sensor_avg_data
import api_switch_stats
import sensor_log_report
import monthly_switch_usage_report
import settings


async def GetSwitch(req_handler, arg):
    """
    :param req_handler: http request
    :param arg: {"status_only": boolean, "token"}
    :return: {"devices": [zb device,...]}
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
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
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def OpenSwitch(req_handler, para):
    """
    :param sessionid:
    :param para: {"deviceids", "working_seconds": 0, "token"}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        if para['working_seconds'] < 15:
            raise rg_lib.RGError(rg_lib.ErrorType.ServerErr('working seconds >= 15 '))
        await api_switch_action.Open(para['switchids'], rg_lib.DateTime.utc(),
                                     para['working_seconds'])
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def CloseSwitch(req_handler, para):
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        await api_switch_action.Close(para['switchids'])
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


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


async def AddSchedule(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"schedule": schedule tbl}
    :return: {deviceids, data_tbl: deviceid->[schedule id,...]}
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        temp = para['schedule']
        temp['second'] = 0
        return __AddSchedule(temp)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RemoveSchedule(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"scheduleids": [id,...]}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        sql_rows = []
        for sid in para['scheduleids']:
            sql_rows.append(["delete from rgw_switch_schedule_switch where scheduleid=?", (sid,)])
            sql_rows.append(["delete from rgw_switch_schedule where id=?", (sid,)])
        await api_switch_schedule.Remove(sql_rows)
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def ListSchedule(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"search_no": all, valid invalid}
    :return: [schedule obj,...]
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
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
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetSensor(req_handler, para):
    """
    :param req_handler:
    :param para: {}
    :return: {groupids: [groupid,...], data_tbl: {groupid->[sensor data]}}
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        if "sensorids" in para:
            sql_str = rg_lib.Sqlite.GenInClause("""select * from rgw_sensor where id in """,
                                                para['sensorids'])
        else:
            sql_str = """select * from rgw_sensor"""
        return await api_core.Sensor.Query([sql_str, []])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def FindSensorMinsAvgLog(req_handler, para):
    """
        :param para: {"sensorids":[], "start_ts": timestamp, "stop_ts": timestamp,
                      "mins_interval": integer}
                      or {"sensorids":[], "hours": hours range, "mins_interval": integer}
        :return: {"sensorids":[], "log_tbl": {sensorid->[mins data,...]},
                  "sensors_tbl": {sensorid->sensor tbl}, "ts_series": [series of timestamp]}
        """
    try:
        await api_req_limit.CheckHTTP(req_handler)
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
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def FindSensorMinsAvgLog2(req_handler, para):
    """
    log_tbl is sorted by cts
    :param para: {"sensorids":[], "start_ts": timestamp, "stop_ts": timestamp,
                  "mins_interval": integer}
                  or {"sensorids":[], "hours": hours range, "mins_interval": integer}
    :return: {"sensorids":[], "log_tbl": {sensorid->{cts: record,}},
              "sensors_tbl": {sensorid->sensor tbl}, "ts_series": [series of timestamp]}
    """
    result = await FindSensorMinsAvgLog(req_handler, para)
    temp = {}
    for sensorid_str in result['log_tbl']:
        data_list = result['log_tbl'][sensorid_str]
        if sensorid_str not in temp:
            temp[sensorid_str] = collections.OrderedDict()
        for rec in data_list:
            temp[sensorid_str][rec['cts']] = rec
    result['log_tbl'] = temp
    return result


async def ExportSensorMinsAvgLog(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"sensorids":[], "start_ts": timestamp, "stop_ts": timestamp,
                  "mins_interval": integer}
                  or {"sensorids":[], "hours": hours range, "mins_interval": integer,
                  }
    :return: URL
    """
    try:
        await api_auth.CheckRight(para['token'])
        log_tbl = await FindSensorMinsAvgLog2(req_handler, para)
        tz_obj = await api_core.SysCfg.GetTimezone()
        log_tbl['tz_offset'] = tz_obj.utcoffset(rg_lib.DateTime.utc()).total_seconds()
        file_name = "{0}.xlsx".format(bson.ObjectId())
        file_path = os_path.join(settings.WEB['export_path'], file_name)
        await threads.deferToThread(sensor_log_report.Make, file_path, log_tbl)
        return {'url': os_path.join('/', rgw_consts.URLs.EXPORT_FMT.format(file_name))}
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetSwitchOnDetail(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"switchid": deviceid, "start_ts": timestamp,
                  "stop_ts": timestamp, "search_no": "range" or "monthly",
                  "year": year, "month": month}
    :return: {"recs": [], 'total_val': xx}
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        tz_obj = await api_core.SysCfg.GetTimezone()
        if para['search_no'] == 'range':
            log_tbl = await api_switch_stats.GetDetail(para['switchid'], para['start_ts'], para['stop_ts'])
        else:
            usages = await api_switch_stats.GetMonthlyUsage(para['year'], para['month'], para['switchid'],
                                                            tz_obj)
            log_tbl = {'recs': usages}
            log_tbl['total_val'] = sum([rec['val'] for rec in log_tbl['recs']])
        return log_tbl
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetLatestTriggerLog(req_handler, para):
    """
    :param req_handler:
    :param para: {"count": xxx, "token"}
    :return: TriggerLog
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_core.TriggerLog.GetLatest(para['count'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def UpdateDeviceName(req_handler, para):
    """
    :param req_handler:
    :param para: {"arg", "token"}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        if para['arg']['type'] == 'switch':
            await api_core.Switch.UpdateName(para['arg']['id'], para['arg']['name'], para['arg']['tag'])
        else:
            await api_core.Sensor.UpdateName(para['arg']['id'], para['arg']['name'], para['arg']['tag'])
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def ListSwitchMonthlyUsage(req_handler, para):
    """
    :param req_handler:
    :param para: {year, month, token}
    :return: {"switches": [switch modls], "rec_tbl": {switchid:[SwitchOpDuration,...]}}
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        tz_obj = await api_core.SysCfg.GetTimezone()
        switches = await api_core.Switch.Query(["select id, name from rgw_switch", []])
        result = {'switches': switches, 'rec_tbl': {}}
        for i in switches:
            usages = await api_switch_stats.GetMonthlyUsage(para['year'], para['month'], i['id'],
                                                            tz_obj)
            result['rec_tbl'][i['id']] = usages
        return result
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def ExportSwitchMonthlyUsage(req_handler, para):
    """
    :param req_handler:
    :param para: {year, month, token}
    :return: url
    """
    try:
        arg = await ListSwitchMonthlyUsage(req_handler, para)
        arg['year'], arg['month'] = para['year'], para['month']
        file_name = "{0}.xlsx".format(bson.ObjectId())
        file_path = os_path.join(settings.WEB['export_path'], file_name)
        await threads.deferToThread(monthly_switch_usage_report.Make, file_path, arg)
        return {'url': os_path.join('/', rgw_consts.URLs.EXPORT_FMT.format(file_name))}
    except Exception:
        rg_lib.Cyclone.HandleErrInException()

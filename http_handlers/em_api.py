from twisted.python import log
import rg_lib
import api_em
import api_core
import api_req_limit
import api_auth


async def GetSwitch(req_handler, arg):
    """
    :param req_handler: http request
    :param arg: {"status_only": boolean, "token"}
    :return: {"devices": [zb device,...]}
    """
    try:
        await api_req_limit.CheckMinuteRate("GetSwitch", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(arg['token'])
        return await api_em.GetSwitch(arg)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def OpenSwitch(req_handler, para):
    """
    :param sessionid:
    :param para: {"deviceids", "working_seconds": 0, "token"}
    :return:
    """
    try:
        await api_req_limit.CheckMinuteRate("OpenSwitch", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_em.OpenSwitch(para)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def CloseSwitch(req_handler, para):
    try:
        await api_req_limit.CheckMinuteRate("CloseSwitch", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_em.CloseSwitch(para['switchids'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def AddSchedule(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"schedule": schedule tbl}
    :return: {deviceids, data_tbl: deviceid->[schedule id,...]}
    """
    try:
        await api_req_limit.CheckMinuteRate("AddSchedule", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_em.AddSchedule(para)
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
        await api_req_limit.CheckMinuteRate("RemoveSchedules", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_em.RemoveSchedule(para)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetUserSchedules(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"search_no": all, valid invalid}
    :return: [schedule obj,...]
    """
    try:
        await api_req_limit.CheckMinuteRate("GetUserSchedules", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_em.GetUserSchedules(para)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetSensor(req_handler, para):
    """
    :param req_handler:
    :param para: {}
    :return: {groupids: [groupid,...], data_tbl: {groupid->[sensor data]}}
    """
    try:
        await api_req_limit.CheckMinuteRate("GetSensor", rg_lib.Cyclone.TryGetRealIp(req_handler))
        return await api_em.GetSensor(para)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def FindSensorMinsAvgLog(req_handler, para):
    try:
        await api_req_limit.CheckMinuteRate("FindSensorMinsAvgLog", rg_lib.Cyclone.TryGetRealIp(req_handler), 4)
        return await api_em.FindSensorMinsAvgLog(para)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


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
        await api_req_limit.CheckMinuteRate("ExportSensorMinsAvgLog", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_em.ExportSensorMinsAvgLog(para)
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
        await api_req_limit.CheckMinuteRate("GetSwitchOnDetail", rg_lib.Cyclone.TryGetRealIp(req_handler), 4)
        await api_auth.CheckRight(para['token'])
        return await api_em.GetSwitchOnDetail(para)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetLatestTriggerLog(req_handler, para):
    """
    :param req_handler:
    :param para: {"count": xxx, "token"}
    :return: TriggerLog
    """
    try:
        await api_req_limit.CheckMinuteRate("GetLatestTriggerLog", rg_lib.Cyclone.TryGetRealIp(req_handler), 4)
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
        await api_req_limit.CheckMinuteRate("UpdateDeviceName", rg_lib.Cyclone.TryGetRealIp(req_handler))
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
        await api_req_limit.CheckMinuteRate("ListSwitchMonthlyUsage", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_em.ListSwitchMonthlyUsage(para)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def ExportSwitchMonthlyUsage(req_handler, para):
    """
    :param req_handler:
    :param para: {year, month, token}
    :return: url
    """
    try:
        await api_req_limit.CheckMinuteRate("ExportSwitchMonthlyUsage", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_em.ExportSwitchMonthlyUsage(para)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()

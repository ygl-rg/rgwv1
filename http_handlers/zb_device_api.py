from twisted.python import log
import rg_lib
import api_req_limit
import api_auth
import api_rxg


async def Remove(req_handler, arg):
    """
    :param req_handler: http request
    :param arg: {"deviceids", "token"}
    :return: ok
    """
    try:
        await api_req_limit.CheckMinuteRate("RemoveDevice", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(arg['token'])
        return await api_rxg.ZbDevice.Remove(arg['deviceids'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def Reset(req_handler, para):
    """
    :param req_handler:
    :param para: {"deviceids", "working_seconds": 0, "token"}
    :return:
    """
    try:
        await api_req_limit.CheckMinuteRate("ResetDevice", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbDevice.Reset(para['deviceids'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def Add(req_handler, para):
    try:
        await api_req_limit.CheckMinuteRate("AddDevice", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbDevice.Add(para['device'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def Set(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"schedule": schedule tbl}
    :return: {deviceids, data_tbl: deviceid->[schedule id,...]}
    """
    try:
        await api_req_limit.CheckMinuteRate("SetDevice", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbDevice.Set(para['device'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def Get(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"scheduleids": [id,...]}
    :return:
    """
    try:
        await api_req_limit.CheckMinuteRate("GetDevice", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbDevice.Get(para['deviceid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def Search(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"search_no": all, valid invalid}
    :return: [schedule obj,...]
    """
    try:
        await api_req_limit.CheckMinuteRate("SearchDevice", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        res = await api_rxg.ZbDevice.Search(para['arg'])
        log.msg(res)
        return res
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetOpLog(req_handler, para):
    """
    :param req_handler:
    :param para: {}
    :return: {groupids: [groupid,...], data_tbl: {groupid->[sensor data]}}
    """
    try:
        await api_req_limit.CheckMinuteRate("GetOpLog", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbDevice.GetOpLog(para['deviceid'], para['start_ts'], para['stop_ts'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetOpErrorCount(req_handler, para):
    """
    :param req_handler:
    :param para: {}
    :return: {groupids: [groupid,...], data_tbl: {groupid->[sensor data]}}
    """
    try:
        await api_req_limit.CheckMinuteRate("GetOpErrorCount", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbDevice.GetOpErrorCount(para['start_ts'], para['stop_ts'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetNId(req_handler, para):
    """
    :param req_handler:
    :param para: {}
    :return: {groupids: [groupid,...], data_tbl: {groupid->[sensor data]}}
    """
    try:
        await api_req_limit.CheckMinuteRate("GetNId", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbDevice.GetNId(para['deviceid'], para['moduleid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def Reboot(req_handler, para):
    """
    :param req_handler:
    :param para: {}
    :return: {groupids: [groupid,...], data_tbl: {groupid->[sensor data]}}
    """
    try:
        await api_req_limit.CheckMinuteRate("RebootDevice", rg_lib.Cyclone.TryGetRealIp(req_handler))
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbDevice.Reboot(para['deviceids'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()

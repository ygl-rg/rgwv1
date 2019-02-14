from twisted.python import log
import rg_lib
import api_req_limit
import api_auth
import api_rxg


async def ListModule(req_handler, arg):
    """
    :param req_handler: http request
    :param arg: {"status_only": boolean, "token"}
    :return: {"devices": [zb device,...]}
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        return await api_rxg.ZbModule.ListModule(arg['list_no'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def ProbeDevice(req_handler, para):
    """
    :param req_handler:
    :param para: {"deviceids", "working_seconds": 0, "token"}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbModule.ProbeDevice(para['moduleid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def ResetModule(req_handler, para):
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbModule.ResetModule(para['moduleid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def BackupModule(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"schedule": schedule tbl}
    :return: {deviceids, data_tbl: deviceid->[schedule id,...]}
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbModule.BackupModule(para['moduleid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RestoreModule(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"scheduleids": [id,...]}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbModule.RestoreModule(para['src_moduleid'],
                                                    para['target_moduleid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RebootModule(req_handler, para):
    """
    :param req_handler:
    :param sessionid:
    :param para: {"search_no": all, valid invalid}
    :return: [schedule obj,...]
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbModule.RebootModule(para['moduleid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RebootAll(req_handler, para):
    """
    :param req_handler:
    :param para: {}
    :return: {groupids: [groupid,...], data_tbl: {groupid->[sensor data]}}
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_rxg.ZbModule.RebootAll()
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


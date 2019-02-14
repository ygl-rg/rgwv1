import rg_lib
import api_core
import api_req_limit
import api_auth


def __SearchSensorTrigger(para):
    sql_str = """select r1.id,  
                         r1.start_ts,
                         r1.stop_ts,
                         r1.name
                  from rgw_sensor_trigger r1"""
    sql_args = []
    return api_core.BizDB.Query([sql_str, sql_args])


async def FindTrigger(req_handler, para):
    """
    :param req_handler:
    :param para: {"name": xxx, "val": xxx, "token"}
    :return: user notice expr rows
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await __SearchSensorTrigger(para)
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def SetTrigger(req_handler, arg):
    """
    :param req_handler:
    :param arg: {"trigger", "token"}
    :return: conditional action
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        return await api_core.SensorTrigger.Upsert(arg['trigger'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RemoveTrigger(req_handler, arg):
    """
    :param req_handler:
    :param arg: {"token", "triggerids"}
    :return: string
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        await api_core.SensorTrigger.Remove(arg['triggerids'])
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetTrigger(req_handler, arg):
    """
    :param req_handler:
    :param arg: {token, triggerid}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        return await api_core.SensorTrigger.GetMdl(arg['triggerid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


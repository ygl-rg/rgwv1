import rg_lib
import api_core
import api_xy_device
import api_req_limit
import api_auth


async def __GetSwitch(rowid):
    tbl = await api_core.Switch.Get(["""select r1.* from rgw_switch r1 where r1.id=?""", (rowid,)])
    return tbl


async def AddSwitch(req_handler, arg):
    """
    :param req_handler:
    :param arg: {"switch": switch obj, token}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        await api_core.Switch.Add(arg['switch'])
        return await __GetSwitch(arg['switch']['id'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RemoveSwitch(req_handler, arg):
    """
    :param req_handler:
    :param arg: {token, switchids}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        await api_core.Switch.Remove(arg['switchids'])
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def SetSwitch(req_handler, arg):
    """
    :param req_handler:
    :param arg: {"switch": sensor obj, token}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        await api_core.Switch.Update(arg['switch'])
        return await __GetSwitch(arg['switch']['id'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetSwitch(req_handler, arg):
    """
    :param req_handler:
    :param arg: {token, switchid}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        return await __GetSwitch(arg['switchid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def SearchSwitch(req_handler, para):
    """
    :param req_handler:
    :param para: {"name": xxx, "val": xxx, token}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_core.Switch.Search(para)
    except Exception as e:
        rg_lib.Cyclone.HandleErrInException()


async def SyncSwitch(req_handler, arg):
    """
    :param req_handler:
    :param arg: {token}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        await api_xy_device.SyncSwitch()
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()

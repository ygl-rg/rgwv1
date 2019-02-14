import rg_lib
import api_core
import api_xy_device
import api_req_limit
import api_auth


async def __GetSensor(sensorid):
    return await api_core.Sensor.Get(["""select r1.* from rgw_sensor r1 where r1.id=?""", (sensorid,)])


async def AddSensor(req_handler, arg):
    """
    :param req_handler:
    :param arg: {"sensor": sensor obj}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        return await __GetSensor(await api_core.Sensor.Add(arg['sensor']))
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RemoveSensor(req_handler, arg):
    """
    :param req_handler:
    :param arg: {'sensorids": xx, 'token'}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        await api_core.Sensor.Remove(arg['sensorids'])
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def SetSensor(req_handler, arg):
    """
    :param req_handler:
    :param arg: {"sensor": sensor obj}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        await api_core.Sensor.Update(arg['sensor'])
        return await __GetSensor(arg['sensor']['id'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetSensor(req_handler, arg):
    """
    :param req_handler:
    :param arg: {sensorid, token}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        return await api_core.Sensor.ById(arg['sensorid'])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def SearchSensor(req_handler, para):
    """
    :param req_handler:
    :param para: {"name": xxx, "val": xxx, token}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_core.Sensor.Search(para)
    except Exception as e:
        rg_lib.Cyclone.HandleErrInException()


async def SyncSensor(req_handler, arg):
    """
    :param req_handler:
    :param arg:
    :return: "ok"
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        await api_xy_device.SyncSensor()
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


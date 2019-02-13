import json
from twisted.internet import error, defer
import treq
import rg_lib
import api_core
import node_models as models
import rgw_consts

MAX_OP_COUNT = 1000


async def IncrOpCount(deviceid):
    key = rgw_consts.Keys.DEVICE_OP_COUNT.format(deviceid)
    return await api_core.BizDB.redis_conn.incr(key)


async def IsOverflow(deviceid):
    key = rgw_consts.Keys.DEVICE_OP_COUNT.format(deviceid)
    bytes_obj = await api_core.BizDB.redis_conn.get(key)
    if bytes_obj:
        return int(bytes_obj) > MAX_OP_COUNT
    else:
        return False


async def RemoveOpCount(deviceid):
    return await api_core.BizDB.redis_conn.delete(rgw_consts.Keys.DEVICE_OP_COUNT.format(deviceid))


async def Req(rpc_no, method, params, timeout):
    tbl = {'id': 1,
           'method': method,
           'params': params}
    try:
        url, pwd = await api_core.SysCfg.GetGwApiUrl(rpc_no)
        if url:
            tbl['params'][0]['token'] = pwd
            resp_defer = await treq.post(url, data=json.dumps(tbl).encode('utf-8'), timeout=timeout)
            res = await resp_defer.json()
            if res['error']:
                raise rg_lib.RGError(res['error'])
            else:
                return res['result']
        else:
            raise ValueError('Invalid Url')
    except error.TimeoutError:
        raise rg_lib.RGError(rg_lib.ErrorType.Timeout())
    except defer.CancelledError:
        raise rg_lib.RGError(rg_lib.ErrorType.Timeout())


async def EMReq(method, params, timeout):
    return await Req('rxg/api/em', method, params, timeout)


async def ZbModuleReq(method, params, timeout):
    return await Req('rxg/api/zbmoduleadm', method, params, timeout)


async def ZbDeviceReq(method, params, timeout):
    return await Req('rxg/api/zbdeviceadm', method, params, timeout)


def ListModule(list_no):
    return ZbModuleReq('ListModule', [{'list_no': list_no}], 3)


def ProbeDevice(moduleid):
    return ZbModuleReq('ProbeDevice', [{'moduleid': moduleid}], 600)


def ListDevice(list_no):
    """
    :return: list of devices
    """
    return EMReq('ListDevice', [{'list_no': list_no}], 3)


async def ReadDevice(deviceids, valid_vals_only):
    """
    :param deviceids:
    :return: list of devices
    """
    devs = await EMReq('ReadDevice', [{'deviceids': deviceids}], (len(deviceids) + 1) * 100)
    if valid_vals_only:
        return [dev for dev in devs if models.XYDevice.ValsNotEmpty(dev)]
    else:
        return devs


async def GetSensorVal(sensorids):
    devids = models.Sensor.ExtractDeviceId(sensorids)
    result = []
    try:
        devs = await ReadDevice(devids, True)
        result.extend(devs)
    except rg_lib.RGError:
        pass
    return result


async def OpenSwitch(switchid):
    """
    :param switchid: [{switchid}]
    :return: if succeeds, return a device otherwise None
    """
    arg = {'deviceid': switchid}
    dev = await EMReq('OpenSwitch', [{'arg': arg}], 100)
    res = dev if (models.XYDevice.ValsNotEmpty(dev) and dev['vals'][0] == models.SwitchAction.ON) else None
    return res


async def CloseSwitch(switchid):
    """
    :param switch id
    :return: device
    """
    dev = await EMReq('CloseSwitch',
                      [{
                          "arg": {'deviceid': switchid}
                      }], 100)
    res = dev if (models.XYDevice.ValsNotEmpty(dev) and dev['vals'][0] == models.SwitchAction.OFF) else None
    return res


async def RebootDevice(deviceids):
    return await ZbDeviceReq('RebootDevice', [{"deviceids": deviceids}], 10)


async def RebootAll():
    return await ZbModuleReq('RebootAll', [{}], 10)

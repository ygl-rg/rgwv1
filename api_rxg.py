import json
from twisted.internet import error, defer
import treq
import rg_lib
import api_core
import node_models as models


async def Req(rpc_no, method, params, timeout):
    tbl = {'id': 1,
           'method': method,
           'params': params}
    try:
        url = await api_core.SysCfg.GetGwApiUrl(rpc_no)
        if url:
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


class ZbModule:
    @classmethod
    async def Req(cls, method, params, timeout):
        return await Req('rxg/api/zbmoduleadm', method, params, timeout)

    @classmethod
    async def ListModule(cls, list_no):
        return await cls.Req('ListModule', [{'list_no': list_no}], 3)

    @classmethod
    async def ProbeDevice(cls, moduleid):
        return await cls.Req('ProbeDevice', [{'moduleid': moduleid}], 600)

    @classmethod
    async def ResetModule(cls, moduleid):
        return await cls.Req('ResetModule', [{'moduleid': moduleid}], 600)

    @classmethod
    async def BackupModule(cls, moduleid):
        return await cls.Req('BackupModule', [{'moduleid': moduleid}], 600)

    @classmethod
    async def RestoreModule(cls, src_moduleid, target_moduleid):
        return await cls.Req('RestoreModule', [{'src_moduleid': src_moduleid,
                                                'target_moduleid': target_moduleid}], 600)

    @classmethod
    async def RebootModule(cls, moduleid):
        return await cls.Req('RebootModule', [{'moduleid': moduleid}], 600)

    @classmethod
    async def RebootAll(cls):
        return await cls.Req('RebootAll', [{}], 600)


class ZbDevice:
    @classmethod
    async def Req(cls, method, params, timeout):
        return await Req('rxg/api/zbdeviceadm', method, params, timeout)


class EM:
    @classmethod
    async def Req(cls, method, params, timeout):
        return await Req('rxg/api/em', method, params, timeout)


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

import json
from twisted.internet import error, defer
import treq
import rg_lib
import api_core
import models


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


class ZbModule:
    @classmethod
    async def Req(cls, method, params, timeout):
        return await Req('api/zbmoduleadm', method, params, timeout)

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
        return await Req('api/zbdeviceadm', method, params, timeout)

    @classmethod
    async def Add(cls, device_mdl):
        return await cls.Req('AddDevice', [{'device': device_mdl}], 10)

    @classmethod
    async def Set(cls, device_mdl):
        return await cls.Req('SetDevice', [{'device': device_mdl}], 10)

    @classmethod
    async def Get(cls, deviceid):
        return await cls.Req('GetDevice', [{'deviceid': deviceid}], 10)

    @classmethod
    async def Remove(cls, deviceids):
        return await cls.Req('RemoveDevice', [{'deviceids': deviceids}], len(deviceids)*10+1)

    @classmethod
    async def Reset(cls, deviceids):
        return await cls.Req('ResetDevice', [{'deviceids': deviceids}], len(deviceids)*10+1)

    @classmethod
    async def Search(cls, arg):
        return await cls.Req('SearchDevice', [arg], 10)

    @classmethod
    async def GetOpLog(cls, deviceid, start_ts, stop_ts):
        return await cls.Req('GetDeviceOpLog', [{'deviceid': deviceid,
                                                 'start_ts': start_ts,
                                                 'stop_ts': stop_ts}], 10)

    @classmethod
    async def GetOpErrorCount(cls, start_ts, stop_ts):
        return await cls.Req('GetDeviceOpErrorCount', [{'start_ts': start_ts,
                                                        'stop_ts': stop_ts}], 10)

    @classmethod
    async def GetNId(cls, deviceid, moduleid):
        return await cls.Req('GetDeviceNId', [{'deviceid': deviceid, 'moduleid': moduleid}], 20)

    @classmethod
    async def Reboot(cls, deviceids):
        return await cls.Req('RebootDevice', [{'deviceids': deviceids}], len(deviceids)*3+1)


class EM:
    @classmethod
    async def Req(cls, method, params, timeout):
        return await Req('api/em', method, params, timeout)

    @classmethod
    def ListDevice(cls, list_no):
        """
        :return: list of devices
        """
        return cls.Req('ListDevice', [{'list_no': list_no}], 3)

    @classmethod
    async def ReadDevice(cls, deviceids, valid_vals_only):
        """
        :param deviceids:
        :return: list of devices
        """
        devs = await cls.Req('ReadDevice', [{'deviceids': deviceids}], (len(deviceids) + 1) * 100)
        if valid_vals_only:
            return [dev for dev in devs if models.XYDevice.ValsNotEmpty(dev)]
        else:
            return devs

    @classmethod
    async def GetSensorVal(cls, sensorids):
        devids = models.Sensor.ExtractDeviceId(sensorids)
        result = []
        try:
            devs = await cls.ReadDevice(devids, True)
            result.extend(devs)
        except rg_lib.RGError:
            pass
        return result

    @classmethod
    async def OpenSwitch(cls, switchid):
        """
        :param switchid: [{switchid}]
        :return: if succeeds, return a device otherwise None
        """
        arg = {'deviceid': switchid}
        dev = await cls.Req('OpenSwitch', [{'arg': arg}], 100)
        res = dev if (models.XYDevice.ValsNotEmpty(dev) and dev['vals'][0] == models.SwitchAction.ON) else None
        return res

    @classmethod
    async def CloseSwitch(cls, switchid):
        """
        :param switch id
        :return: device
        """
        dev = await cls.Req('CloseSwitch',
                          [{
                              "arg": {'deviceid': switchid}
                          }], 100)
        res = dev if (models.XYDevice.ValsNotEmpty(dev) and dev['vals'][0] == models.SwitchAction.OFF) else None
        return res

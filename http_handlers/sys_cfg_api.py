from twisted.internet import defer, reactor
from twisted.python import log
import rg_lib
import api_core
import api_req_limit
import api_xy_device
import api_auth
import settings


async def SetCfg(req_handler, para):
    """
    :param req_handler:
    :param para: {"cfg": {}, "token"}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        await api_core.SysCfg.Set(para['cfg'])
        reactor.callLater(3, defer.ensureDeferred, api_core.PageKite.RestartBackend(settings.HTTP_PORT))
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def GetCfg(req_handler, para):
    """
    :param req_handler:
    :param para: {token}
    :return:
    """
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(para['token'])
        return await api_core.SysCfg.Get(["select * from rgw_sys_cfg", tuple()])
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RebootSys(req_handler, arg):
    """
    :param req_handler:
    :param arg: {token}
    :return:
    """
    from twisted.internet import reactor
    try:
        await api_auth.CheckRight(arg['token'])
        tp = rg_lib.ProcessProto('reboot')
        reactor.spawnProcess(tp, '/sbin/reboot', ['/sbin/reboot'], {})
        return 'ok'
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RestartSys(req_handler, arg):
    import os
    try:
        await api_auth.CheckRight(arg['token'])
        rg_lib.Process.Kill(os.getpid())
        return 'ok'
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def RegisterDevice(req_handler, arg):
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        devs = await api_xy_device.ProbeAndSync()
        return devs
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


async def SyncDevice(req_handler, arg):
    try:
        await api_req_limit.CheckHTTP(req_handler)
        await api_auth.CheckRight(arg['token'])
        await api_xy_device.SyncSwitch()
        await api_xy_device.SyncSensor()
        return "ok"
    except Exception:
        rg_lib.Cyclone.HandleErrInException()


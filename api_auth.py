import json
import rgw_consts
import api_core
import models


async def Add(pwd):
    mdl, curr_time = models.UserSession.make(pwd)
    key = rgw_consts.Keys.USER_SESSION.format(mdl['sessionid'])
    await api_core.BizDB.redis_conn.set(key, json.dumps(mdl).encode('utf-8'), rgw_consts.Timeout.COOKIE_INTERVAL)
    return mdl['sessionid'], mdl['expiry'], curr_time


def Remove(sessionid):
    key = rgw_consts.Keys.USER_SESSION.format(sessionid)
    return api_core.BizDB.redis_conn.delete(key)


async def Get(sessionid):
    key = rgw_consts.Keys.USER_SESSION.format(sessionid)
    bytes_obj = await api_core.BizDB.redis_conn.get(key)
    if bytes_obj:
        tbl = json.loads(bytes_obj.decode('utf-8'))
        return tbl
    else:
        return None


async def Adm(pwd):
    pwd_str = await CheckUser(pwd)
    sessionid, expire_at, curr = await Add(pwd_str)
    return sessionid, expire_at, curr


async def CheckUser(pwd):
    flag = await api_core.SysCfg.CheckPwd(pwd)
    if flag:
        return pwd
    else:
        raise models.PasswordError()


async def CheckUser2(pwd):
    flag = await api_core.SysCfg.CheckPwd(pwd)
    if flag:
        return pwd
    else:
        raise models.NoRightError()


async def CheckRight(token):
    if token:
        tbl = await Get(token)
        if tbl:
            return tbl['pwd']
        else:
            return await CheckUser2(token)
    else:
        raise models.NoRightError()

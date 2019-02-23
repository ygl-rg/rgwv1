import rgw_consts
import rg_lib
import api_core
import models


def MinuteKey(datetime_obj):
    return "{0}{1}{2}{3}{4}".format(datetime_obj.year, datetime_obj.month, datetime_obj.day,
                                    datetime_obj.hour, datetime_obj.minute)


async def CheckMinuteRate(prefix, ip, rate=100):
    curr = rg_lib.DateTime.utc()
    key = rgw_consts.Keys.MINUTE_RATE_FMT.format(prefix, MinuteKey(curr), ip)
    count = await api_core.BizDB.redis_conn.get(key)
    if (count is not None) and (int(count) > rate):
        raise models.AccessOverLimit()
    else:
        pl_obj = await api_core.BizDB.redis_conn.pipeline()
        pl_obj.incr(key)
        pl_obj.expire(key, 60)
        await pl_obj.execute_pipeline()
        return True


async def CheckHTTP(req_handler, rate=200):
    return await CheckMinuteRate('http', rg_lib.Cyclone.TryGetRealIp(req_handler), rate)


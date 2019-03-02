from twisted.python import log
import rg_lib
import api_core
import api_sensor_data
import settings


async def Run():
    try:
        curr_ts = rg_lib.DateTime.ts()
        await api_sensor_data.RemoveTTL(curr_ts - settings.LOG_DB['ttl'])
        await api_core.TriggerLog.RemoveTTL(curr_ts - settings.LOG_DB['ttl'])
    except Exception:
        log.err()




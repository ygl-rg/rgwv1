import datetime
from twisted.python import log
import rg_lib
import api_core
import api_sensor_data
import api_sensor_avg_data
import models


async def Run():
    try:
        curr_dt = rg_lib.DateTime.utc()
        sensors = await api_core.BizDB.Query(["select id from rgw_sensor", []])
        sensorids = [s['id'] for s in sensors]
        start_dt = (curr_dt - datetime.timedelta(seconds=60)).replace(second=0)
        mdls = []
        for sid in sensorids:
            row = await api_sensor_data.GetMinAvg(start_dt, curr_dt, sid, True)
            if row:
                mdls.append(models.SensorAvgData.Sync(row))
        if len(mdls) > 0:
            await api_sensor_avg_data.Add(mdls)
    except Exception:
        log.err()




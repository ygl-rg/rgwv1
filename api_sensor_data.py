import models
import api_core
import rg_lib


def Add(sensor_data):
    """
    :param sensor_data: models.SensorData or list of models.SensorData
    :return:
    """
    sql_rows = []
    if isinstance(sensor_data, list):
        for mdl in sensor_data:
            sql_rows.append(models.SensorData.DynInsert(mdl, True))
    else:
        sql_rows.append(models.SensorData.DynInsert(sensor_data, True))
    return api_core.LogDB.Interaction(sql_rows)


async def GetMinAvg(start_dt, stop_dt, sensorid, exclude_max_min):
    """
    fetching average value without max and min, it can help for smooth value
    :param start_dt:
    :param stop_dt:
    :param sensorid:
    :param exclude_max_min: boolean, if True, max and min value will be excluded.
    :return:
    """
    start_ts, stop_ts = rg_lib.DateTime.dt2ts(start_dt), rg_lib.DateTime.dt2ts(stop_dt)
    if exclude_max_min:
        sql_str = """with max_min_cte(sensorid, cts, val) as 
                      (select r1.sensorid, r1.cts, max(r1.val) 
                       from rgw_sensor_data r1
                       where r1.sensorid=? and r1.cts>=? and r1.cts<? UNION 
                       select r1.sensorid, r1.cts, min(r1.val) 
                       from rgw_sensor_data r1
                       where r1.sensorid=? and r1.cts>=? and r1.cts<?)

                       select cast(strftime('%s', strftime('%Y-%m-%d %H:%M', r1.cts, 'unixepoch')) as integer) cts,
                              avg(r1.val) avg_val, r1.sensorid, r1.data_no 
                       from rgw_sensor_data r1
                       where r1.sensorid =? and r1.cts>=? and r1.cts<? and r1.cts not in (select cts from max_min_cte) 
                  """
        sql_args = [sensorid, start_ts,stop_ts,
                    sensorid, start_ts, stop_ts,
                    sensorid, start_ts, stop_ts]
    else:
        sql_str = """select cast(strftime('%s', strftime('%Y-%m-%d %H:%M', r1.cts, 'unixepoch')) as integer) cts,
                            avg(r1.val) avg_val, r1.sensorid, r1.data_no 
                     from rgw_sensor_data r1
                     where r1.sensorid =? and r1.cts>=? and r1.cts<?"""
        sql_args = [sensorid, start_ts, stop_ts]
    rows = await api_core.LogDB.Query([sql_str, sql_args])
    if len(rows) > 0:
        return rows[0] if (rows[0]['avg_val'] is not None) else None
    else:
        return None


async def GetLatestAvg(sensorid):
    curr_ts = rg_lib.DateTime.ts()
    return await GetMinAvg(curr_ts - 60, curr_ts, sensorid, False)


def RemoveTTL(ts_val):
    return api_core.LogDB.Interaction([
        ["delete from rgw_sensor_data where cts < ?", (ts_val,)]
    ])

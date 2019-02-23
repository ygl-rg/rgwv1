import models
import api_core
import rg_lib

MINS = 3


def Add(sensor_data):
    """
    :param sensor_data: models.SensorAvgData or list of models.SensorData
    :return:
    """
    sql_rows = []
    if isinstance(sensor_data, list):
        for mdl in sensor_data:
            sql_rows.append(models.SensorAvgData.DynInsert(mdl, True))
    else:
        sql_rows.append(models.SensorAvgData.DynInsert(sensor_data, True))
    return api_core.LogDB.Interaction(sql_rows)


def QueryMinAvg(start_dt, stop_dt, sensorids, mins_interval, count=10000):
    sql_str = rg_lib.Sqlite.GenInSql("""with
                                            mins_cte(max_ts,min_ts) as
                                        (select strftime('%s', strftime('%Y-%m-%d %H:%M', min(cts), 'unixepoch', '+{0} minutes')),
                                         min(cts) from rgw_sensor_avg_data where cts>= ? and cts <?
                                         and strftime('%M',cts,'unixepoch')%?=0 group by strftime('%Y-%m-%d %H:%M', cts, 'unixepoch') limit {1})
                                         select cast(strftime('%s', strftime('%Y-%m-%d %H:%M', m1.min_ts, 'unixepoch')) as integer) cts,
                                         avg(r1.val) avg_val, r1.sensorid, r1.data_no from
                                         rgw_sensor_avg_data r1 inner join mins_cte m1 on
                                         (r1.cts>=m1.min_ts and r1.cts<m1.max_ts) where r1.sensorid in
                  """.format(mins_interval, count), sensorids)
    sql_str += """ group by strftime('%Y-%m-%d %H:%M', m1.min_ts, 'unixepoch'),r1.sensorid limit {0}""".format(
        count)
    sql_args = [rg_lib.DateTime.dt2ts(start_dt),
                rg_lib.DateTime.dt2ts(stop_dt), mins_interval] + sensorids
    return api_core.LogDB.Query([sql_str, sql_args])

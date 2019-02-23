import collections
import rg_lib
import models
import api_core


async def QueryMdl(sql_row):
    mdls = await api_core.BizDB.Query(sql_row)
    ids = [mdl['id'] for mdl in mdls if 'id' in mdl]
    if len(ids) > 0:
        relation_tbl = await GetSwitchInfoTbl(ids)
        for mdl in mdls:
            mdl['switches'] = list(relation_tbl[mdl['id']])
    return mdls


async def GetSwitchInfoTbl(scheduleids):
    """
    :param scheduleids:
    :return: {scheduleid -> switches}
    """
    sql_str = rg_lib.Sqlite.GenInSql("""select r1.scheduleid, r1.switchid, r2.name switch_name 
                                           from rgw_switch_schedule_switch r1, rgw_switch r2
                                            where r1.switchid=r2.id and r1.scheduleid in """, scheduleids)
    rows = await api_core.BizDB.Query([sql_str, scheduleids])
    res = collections.defaultdict(list)
    for row in rows:
        res[row['scheduleid']].append(row)
    return res


def Add(schedule_mdl):
    sql_rows = models.SwitchSchedule.DynInsert(schedule_mdl)
    return api_core.BizDB.Interaction(sql_rows)


def GetDueSchedules(dt_obj):
    """
    :param dt_obj:
    :return: [schedule,...]
    """
    sql_str = """select * from rgw_switch_schedule
                      where next_run_ts <= ? order by next_run_ts asc limit 100"""
    return QueryMdl([sql_str, (rg_lib.DateTime.dt2ts(dt_obj),)])


def Remove(sql_rows):
    return api_core.BizDB.Interaction(sql_rows)


def RemoveTTL(ts_val):
    return api_core.BizDB.Interaction([
        ["""delete from rgw_switch_schedule_switch 
                 where scheduleid in (select id from rgw_switch_schedule where (stop_ts < ?) and (next_run_ts is null))""",
         (ts_val,)],
        ["delete from rgw_switch_schedule where (stop_ts < ?) and (next_run_ts is null)",
         (ts_val,)]
    ])


async def CheckConflict(schedule_mdl):
    """
    :param schedule_mdl:
    :return: {switchids, data_tbl: switchid->[a list of schedule id]}
    """
    res = {'switchids': [], 'data_tbl': collections.defaultdict(list)}
    for switchid in schedule_mdl['switchids']:
        sql_str = """select r1.* from rgw_switch_schedule_switch r1, rgw_switch_schedule r2
                          where r1.scheduleid=r2.id and r1.switchid=? and
                                r2.local_start_time=? and r2.local_stop_time=? 
                                and r2.hour=? and r2.minute=? and r2.second=?"""
        sql_args = [switchid, schedule_mdl['local_start_time'],
                    schedule_mdl['local_stop_time'], schedule_mdl['hour'], schedule_mdl['minute'],
                    schedule_mdl['second']]
        tbls = await api_core.BizDB.Query([sql_str, sql_args])
        if len(tbls) > 0:
            res['data_tbl'][switchid] = [i['scheduleid'] for i in tbls]
            res['switchids'].append(switchid)
    return res

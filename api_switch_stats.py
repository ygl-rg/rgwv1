import rg_lib
import models
import api_core

mem_db = rg_lib.Sqlite.MakeMemoryConn()


def Init():
    with mem_db:
        mem_db.execute("BEGIN")
        models.SwitchOpSession.Init(mem_db)


def __GetOpenSession(deviceid):
    with mem_db:
        cur_obj = mem_db.cursor()
        cur_obj.execute("BEGIN")
        sql_str = "select * from rgw_switch_op_session where switchid=? and status=?"
        rows = list(mem_db.execute(sql_str, (deviceid, 'ON')))
        cur_obj.close()
        return rows[0] if len(rows) > 0 else None


def __OpenSession(session):
    with mem_db:
        cur_obj = mem_db.cursor()
        cur_obj.execute('BEGIN')
        cur_obj.execute("insert or ignore into rgw_switch_op_session(switchid, status, uts) values(?,?,?)",
                        (session['switchid'], 'ON', session['uts']))
        cur_obj.execute("select changes() c")
        rows = cur_obj.fetchall()
        cur_obj.close()
        return rows[0]['c']


def AddDuration(duration_mdl):
    return rg_lib.Sqlite.RunInteraction(api_core.LogDB.db_pool, [models.SwitchOpDuration.DynInsert(duration_mdl, True)])


def __CloseSession(switchid, uts):
    with mem_db:
        cur = mem_db.cursor()
        cur.execute("BEGIN")
        cur.execute("select uts from rgw_switch_op_session where switchid=? and status=?",
                    (switchid, 'ON'))
        rows = cur.fetchall()
        if len(rows) > 0:
            if uts > 0:
                cur.execute("update rgw_switch_op_session set uts=? where switchid=?and status=?",
                            (uts, switchid, 'ON'))
            else:
                cur.execute("delete from rgw_switch_op_session where switchid=? and status=?",
                            (switchid, 'ON'))
            cur.close()
            return True, dict(rows[0])
        else:
            cur.close()
            return False, None


async def HandleSession(session):
    has_open = __GetOpenSession(session['switchid'])
    if session['status'] == 'ON':
        if has_open is None:
            __OpenSession(session)
    else:
        if has_open:
            close_succ, doc = __CloseSession(session['switchid'], 0)
            if close_succ:
                stop = session['uts']
                switch_on_seconds = max(doc['uts'], stop) - min(doc['uts'], stop)
                if switch_on_seconds > 1:
                    duration_tbl = models.SwitchOpDuration.make(doc['uts'], stop,
                                                                session['switchid'],
                                                                'ON', switch_on_seconds)
                    await AddDuration(duration_tbl)


async def HandleOpenSession(session, ts_val):
    """
    :param session:
    :param ts_val: timestamp
    :return:
    """
    has_open = __GetOpenSession(session['switchid'])
    if has_open:
        duration = ts_val - has_open['uts']
        if duration > 0:
            op_succ, _ = __CloseSession(session['switchid'], ts_val)
            if op_succ:
                duration_tbl = models.SwitchOpDuration.make(has_open['uts'], ts_val, session['switchid'],
                                                            'ON', duration)
                await AddDuration(duration_tbl)


def GetSum(start_ts, stop_ts, switchid):
    def __helper(sqlite_conn):
        cur = sqlite_conn.cursor()
        cur.execute("BEGIN")
        sql_str = """select switchid, sum(val) val from rgw_switch_op_duration
                     where start_ts>=? and stop_ts<=? and status=? and switchid =?"""
        cur.execute(sql_str, (start_ts, stop_ts, models.Switch.ON, switchid))
        for i in cur:
            return i['val'] if i['val'] else 0
    return api_core.LogDB.db_pool.runWithConnection(__helper)


async def GetMonthlyUsage(year, month, switchid, tz_obj):
    """
        :param year:
        :param month:
        :param switchid: switchid
        :param tz_obj: pytz.timezone
        :return: [daily usage]
    """
    result = []
    day_tbls = rg_lib.DateTime.DayRangesInMonth(year, month, tz_obj)
    for day_tbl in day_tbls:
        val = await GetSum(rg_lib.DateTime.dt2ts(day_tbl['utc_start']),
                           rg_lib.DateTime.dt2ts(day_tbl['utc_stop']),
                           switchid)
        result.append(models.SwitchOpDuration.make(day_tbl['utc_start'], day_tbl['utc_stop'],
                                                   switchid, 'ON', val))
    return result


async def GetDetail(switchid, start, stop):
    """
    :param switchid:
    :param start:
    :param stop:
    :return: {"recs":[SwitchOpDuration,...], "total_val": sum of record['val']}
    """

    def Prediate(arg1, arg2):
        return arg1['start_ts'] == arg2['stop_ts']

    def MergeGroup(group):
        if len(group) == 1:
            return models.SwitchOpDuration.make(group[0]['start_ts'],
                                                group[0]['stop_ts'], group[0]['switchid'],
                                                'ON', (group[0]['stop_ts'] - group[0]['start_ts']))
        else:
            return models.SwitchOpDuration.make(group[0]['start_ts'],
                                                group[-1]['stop_ts'], group[0]['switchid'],
                                                'ON', (group[-1]['stop_ts'] - group[0]['start_ts']))

    def __helper(sqlite_conn):
        sqlite_conn.execute("BEGIN")
        sql_str = """select * from rgw_switch_op_duration where start_ts>=? and stop_ts<=? and 
                          switchid=? and status=?"""
        sql_args = [rg_lib.DateTime.dt2ts(start), rg_lib.DateTime.dt2ts(stop), switchid, 'ON']
        return [rg_lib.Sqlite.FilterRow(i) for i in sqlite_conn.execute(sql_str, tuple(sql_args))]

    rows = await api_core.LogDB.db_pool.runWithConnection(__helper)
    result = {"recs": rows}
    grps = rg_lib.Collect.Grouping(result['recs'], Prediate)
    result['recs'] = [MergeGroup(grp) for grp in grps if len(grp) > 0]
    result['total_val'] = sum([i['val'] for i in result['recs']])
    return result

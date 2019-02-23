from twisted.internet import defer
from twisted.python import log
import models
import rg_lib
import api_core
import api_rxg

lock_tbl = {}


async def Acquire(switchid):
    if switchid not in lock_tbl:
        lock_tbl[switchid] = defer.DeferredLock()
    await lock_tbl[switchid].acquire()


def Release(switchid):
    lock_tbl[switchid].release()


async def __Add(action_mdl):
    try:
        await Acquire(action_mdl['switchid'])
        sql_rows = [
            models.SwitchAction.UpdateExistingAction(action_mdl),
            models.SwitchAction.DynInsert(action_mdl, True)
        ]
        await api_core.BizDB.Interaction(sql_rows)
    finally:
        Release(action_mdl['switchid'])


def Remove(switchids):
    sql_rows = [["delete from rgw_switch_action where switchid=?", (sid,)] for sid in switchids]
    return api_core.BizDB.Interaction(sql_rows)


async def GetReadyOff(dt_obj, switchid):
    """
    stop_ts < dt_obj
    :param dt_obj: datetime or timestamp
    :return:
    """
    temp = """select r1.*
              from rgw_switch_action r1, rgw_switch r2
              where r1.switchid=r2.id and r1.stop_ts <= ? and r1.switchid=?"""
    sql_args = [rg_lib.DateTime.dt2ts(dt_obj), switchid]
    temp_rows = await api_core.BizDB.Query([temp, sql_args])
    return temp_rows[0] if len(temp_rows) > 0 else None


async def GetReadyOn(dt_obj, switchid):
    """
    start_ts < dt_obj < stop_ts and next_run_ts is not null
    :param dt_obj: datetime or timestamp
    :return:
    """
    temp = """select r1.*
                      from rgw_switch_action r1, rgw_switch r2
                      where r1.switchid=r2.id and r1.start_ts < ? and r1.stop_ts > ? 
                      and r1.next_run_ts is not null and r1.switchid=?"""
    ts = rg_lib.DateTime.dt2ts(dt_obj)
    sql_args = [ts, ts, switchid]
    temp_rows = await api_core.BizDB.Query([temp, sql_args])
    return temp_rows[0] if len(temp_rows) > 0 else None


async def Close(switchids):
    for sid in switchids:
        try:
            await Acquire(sid)
            await __Close(sid)
        finally:
            Release(sid)


async def __Close(switchid):
    await Remove([switchid])
    await api_rxg.EM.CloseSwitch(switchid)


async def Open(switchids, dt_obj, working_secs):
    ts_val = rg_lib.DateTime.dt2ts(dt_obj)
    if not isinstance(switchids, list):
        switchids = [switchids]
    actions = [models.SwitchAction.make(devid,
                                        ts_val, ts_val + working_secs,
                                        working_secs) for devid in switchids]
    for action in actions:
        await __Add(action)


async def Open2(arg, dt_obj):
    """
    :param arg: {switchid->working seconds}
    :param dt_obj:
    :return:
    """
    ts_val = rg_lib.DateTime.dt2ts(dt_obj)
    actions = [models.SwitchAction.make(deviceid,
                                        ts_val, ts_val + arg[deviceid], arg[deviceid]) for deviceid in arg]
    for action in actions:
        await __Add(action)


def __UpdateNextStep(sqlite_conn, switchid, dt_obj):
    """
    :param sqlite_conn:
    :param switchid
    :param dt_obj datetime obj
    :return:
    """
    cursor_obj = sqlite_conn.cursor()
    cursor_obj.execute("BEGIN")
    ts_val = rg_lib.DateTime.dt2ts(dt_obj)
    sql_str2 = """update rgw_switch_action 
                      set start_ts=?, stop_ts=?+working_seconds, next_run_ts=null, 
                          op_status=? 
                      where switchid=?"""
    sql_args = (ts_val, ts_val, models.SwitchAction.OP_SUCC, switchid)
    cursor_obj.execute(sql_str2, sql_args)
    cursor_obj.close()


async def UpdateNextStep(switchid, dt_obj):
    await api_core.BizDB.db_pool.runWithConnection(__UpdateNextStep, switchid, dt_obj)


async def DoAction(dt_obj):
    sql_str = "select id from rgw_switch"
    switches = await api_core.BizDB.Query([sql_str, []])
    for i in switches:
        try:
            await Acquire(i['id'])
            action = await GetReadyOn(dt_obj, i['id'])
            if action:
                dev_mdl = await api_rxg.EM.OpenSwitch(action['switchid'])
                if dev_mdl:
                    await UpdateNextStep(action['switchid'], rg_lib.DateTime.utc())
            action = await GetReadyOff(dt_obj, i['id'])
            if action:
                await __Close(action['switchid'])
        finally:
            Release(i['id'])


async def GetSuccOn(switchid):
    """
    :param switchid
    :return: switch action
    """
    curr_ts = rg_lib.DateTime.ts()
    sql_str = """select switchid,  
                            stop_ts, 
                            (stop_ts-{0}) remaining_seconds 
                     from rgw_switch_action 
                     where switchid=? and op_status=?""".format(curr_ts)
    sql_args = [switchid, models.SwitchAction.OP_SUCC]
    actions = await api_core.BizDB.Query([sql_str, sql_args])
    return actions[0] if len(actions) > 0 else None


async def AutoSync():
    sql_str = "select id from rgw_switch"
    sql_str1 = "select switchid, op_status from rgw_switch_action where switchid=?"
    switches = await api_core.BizDB.Query([sql_str, []])
    validids = []
    for i in switches:
        dev_mdls = await api_rxg.EM.ReadDevice([i['id']], True)
        if len(dev_mdls) > 0:
            validids.append(i['id'])
            try:
                await Acquire(i['id'])
                row = await api_core.BizDB.Get([sql_str1, [i['id']]])
                if row:
                    if row['op_status'] == 1:
                        if dev_mdls[0]['vals'][0] == models.SwitchAction.OFF:
                            await api_rxg.EM.OpenSwitch(dev_mdls[0]['id'])
                else:
                    if dev_mdls[0]['vals'][0] == models.SwitchAction.ON:
                        await api_rxg.EM.CloseSwitch(i['id'])
            finally:
                Release(i['id'])
    if len(validids) > 0:
        await api_core.Switch.UpdateUts(validids, rg_lib.DateTime.ts())

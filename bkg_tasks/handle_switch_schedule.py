import rg_lib
import api_core
import api_switch_action
import models


async def RunTask(schedule_mdl, dt_obj):
    """
    if schedule.next_run_ts + working_seconds+1 < dt_obj, just compute the next one
    :param schedule_mdl:
    :param dt_obj:
    :return:
    """
    if (schedule_mdl['next_run_ts'] + schedule_mdl['working_seconds']) > rg_lib.DateTime.dt2ts(dt_obj):
        working_secs = models.SwitchSchedule.ComputeWorkingSecs(schedule_mdl)
        await api_switch_action.Open([s['switchid'] for s in schedule_mdl['switches']],
                                     dt_obj, working_secs)
    ts_tbl = models.SwitchSchedule.ComputeNextRunTs(schedule_mdl)
    sql_row = models.SwitchSchedule.PartialUpdate(ts_tbl, ['id'])
    sql_row[0] += "id=?"
    sql_row[1].append(schedule_mdl['id'])
    await api_core.BizDB.Interaction([sql_row])

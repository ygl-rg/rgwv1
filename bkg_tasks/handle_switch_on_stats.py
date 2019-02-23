from twisted.python import log
import rg_lib
import models
import api_core
import api_switch_action
import api_switch_stats


async def __GetSwtiches():
    """
    :return: (switch on ids, switch off ids)
    """
    rows = await api_core.BizDB.Query(['select id from rgw_switch'])
    onids, offids = [], []
    for row in rows:
        action = await api_switch_action.GetSuccOn(row['id'])
        if action:
            onids.append(row['id'])
        else:
            offids.append(row['id'])
    return onids, offids


async def HandleSession():
    try:
        onids, offids = await __GetSwtiches()
        curr_ts = rg_lib.DateTime.ts()
        for switchid in onids:
            await api_switch_stats.HandleSession(models.SwitchOpSession.Make(switchid, curr_ts, 'ON'))
        for switchid in offids:
            await api_switch_stats.HandleSession(models.SwitchOpSession.Make(switchid, curr_ts, 'OFF'))
    except Exception:
        log.err()


async def HandleOpenSession():
    try:
        onids, offids = await __GetSwtiches()
        curr_ts = rg_lib.DateTime.ts()
        for switchid in onids:
            await api_switch_stats.HandleOpenSession(models.SwitchOpSession.Make(switchid, curr_ts, 'ON'), curr_ts)
        for switchid in offids:
            await api_switch_stats.HandleOpenSession(models.SwitchOpSession.Make(switchid, curr_ts, 'OFF'), curr_ts)
    except Exception:
        log.err()

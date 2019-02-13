from twisted.python import log
import rg_lib
import api_switch_action


async def RunTask():
    try:
        await api_switch_action.DoAction(rg_lib.DateTime.utc())
    except Exception:
        log.err()



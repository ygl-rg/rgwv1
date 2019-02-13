from twisted.internet import defer, task
from twisted.python import log
from apscheduler.schedulers.background import BackgroundScheduler
from twisted.internet import threads
from apscheduler.triggers.cron import CronTrigger
import rg_lib
import api_core
from bkg_tasks import handle_switch_schedule
from bkg_tasks import handle_switch_action
from bkg_tasks import handle_switch_on_stats
import api_scan_device
import api_switch_schedule
from bkg_tasks import remove_ttl_record
from bkg_tasks import sync_sensor_data
from bkg_tasks import reboot_all

scheduler = BackgroundScheduler()
jobs_tbl = {}


async def DoSwitchSchedule():
    try:
        curr = rg_lib.DateTime.utc()
        schedules = await api_switch_schedule.GetDueSchedules(curr)
        for schedule_mdl in schedules:
            try:
                await handle_switch_schedule.RunTask(schedule_mdl, curr)
            except rg_lib.RGError:
                pass
    except Exception:
        log.err()


async def Setup():
    from twisted.internet import reactor
    t_obj1 = task.LoopingCall(lambda: defer.ensureDeferred(DoSwitchSchedule()))
    t_obj1.start(1, False)

    t_obj2 = task.LoopingCall(lambda: defer.ensureDeferred(api_scan_device.ScanSensor()))
    t_obj2.start(12, False)
    jobs_tbl['fetch_sensor_val'] = t_obj2

    t_obj3 = task.LoopingCall(lambda: defer.ensureDeferred(handle_switch_on_stats.HandleSession()))
    t_obj3.start(10, False)

    t_obj4 = task.LoopingCall(lambda: defer.ensureDeferred(api_scan_device.ScanSwitch()))
    t_obj4.start(5, False)
    jobs_tbl['sync_switch_status'] = t_obj4

    t_obj5 = task.LoopingCall(lambda: defer.ensureDeferred(handle_switch_action.RunTask()))
    t_obj5.start(1, False)

    every_mins_trigger_obj = CronTrigger(second=1)
    scheduler.add_job(threads.blockingCallFromThread, every_mins_trigger_obj,
                      args=(reactor, lambda: defer.ensureDeferred(sync_sensor_data.Run())),
                      replace_existing=True, id='sync_sensor_data')

    every_5mins_trigger_obj = CronTrigger(minute='0,5,10,15,20,25,30,35,40,45,50,55', second=59)
    scheduler.add_job(threads.blockingCallFromThread, every_5mins_trigger_obj,
                      args=(reactor, lambda: defer.ensureDeferred(remove_ttl_record.Run())),
                      replace_existing=True, id='remove_ttl')
    scheduler.add_job(threads.blockingCallFromThread, every_5mins_trigger_obj,
                      args=(reactor, lambda: defer.ensureDeferred(handle_switch_on_stats.HandleOpenSession())),
                      replace_existing=True, id='switch_open_session')

    local_tz = await api_core.SysCfg.GetTimezone()
    every_monday_trigger_obj = CronTrigger(day_of_week=0, hour=0, minute=0, second=59, timezone=local_tz)
    scheduler.add_job(threads.blockingCallFromThread, every_monday_trigger_obj,
                      args=(reactor, lambda: defer.ensureDeferred(reboot_all.Run())),
                      replace_existing=True, id='reboot_all_device')

    scheduler.start()


def Close():
    scheduler.shutdown(False)

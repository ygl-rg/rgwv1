import datetime
import pytest
import pytz
import apscheduler.util as aps_util
from apscheduler.triggers.cron import CronTrigger


@pytest.mark.skipif(False, reason='')
class TestAPS(object):
    @pytest.mark.skipif(False, reason='')
    def test_next_fire_time(self):
        trigger_obj2 = CronTrigger(second='5')
        tz_obj = pytz.timezone('UTC')
        curr = datetime.datetime.now(tz_obj)
        next_dt = trigger_obj2.get_next_fire_time(None, curr)
        print next_dt
        assert next_dt == 0






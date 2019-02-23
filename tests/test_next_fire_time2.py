import datetime
import pytest
import models


@pytest.mark.skipif(False, reason='')
class TestNextFireTime(object):
    @pytest.mark.skipif(False, reason='')
    def test_next_fire_time(self):
        newid = models.SwitchSchedule.GenId()
        start_time = datetime.datetime(2018, 1, 1, 16, 0, 0, 0)
        stop_time = datetime.datetime(2018, 10, 3, 23, 59, 59, 0)
        now_dt = datetime.datetime.utcnow()
        hour, minute = 2, 19
        temp = now_dt.replace(hour=hour, minute=minute, second=0)
        if now_dt > temp:
            next_fire = temp + datetime.timedelta(days=1)
        else:
            next_fire = now_dt.replace(hour=hour, minute=minute, second=0)
        print(next_fire)
        assert next_fire > stop_time







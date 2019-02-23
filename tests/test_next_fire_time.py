import datetime
import pytest
import models


@pytest.mark.skipif(False, reason='')
class TestNextFireTime(object):
    @pytest.mark.skipif(False, reason='')
    def test_next_fire_time(self):
        newid = models.SwitchSchedule.GenId()
        start_time = datetime.datetime(2016, 10, 2, 16, 0, 0, 0)
        stop_time = datetime.datetime(2016, 10, 3, 23, 59, 59, 0)
        test = models.SwitchSchedule.make(newid, u"ON", [u'1', u'2'], '2016-10-4',
                                               '2016-12-31', 21, 20, 0, u'UTC', 300, u'root', u'test')
        next_run_ts = models.SwitchSchedule.ComputeNextRunTs(test)
        assert next_run_ts == 0






import datetime
import collections
import pytest
import rg_lib
import sensor_log_report


@pytest.mark.skipif(False, reason='')
class TestReport(object):
    @pytest.mark.skipif(False, reason='')
    def test_sensor_data_report(self):
        result = {
            'sensorids': [u'1', u'2'],
            'log_tbl': {u'1': collections.OrderedDict(), u'2': collections.OrderedDict()},
            'sensor_tbl': {u'1': {u'name': u'soil mositure', u'val_unit': u'%'},
                           u'2': {u'name': u'EC', u'val_unit': u''}},
            'ts_series': [],
            'tz_offset': 8
        }
        start_time = datetime.datetime(2016, 10, 2, 16, 0, 0, 0)
        for i in range(10):
            temp = start_time + datetime.timedelta(minutes=i)
            result['log_tbl'][u'1'][rg_lib.DateTime.dt2ts(temp)] = {'cts': rg_lib.DateTime.dt2ts(temp), 'avg_val': i * 10.0}
            result['log_tbl'][u'2'][rg_lib.DateTime.dt2ts(temp)] = {'cts': rg_lib.DateTime.dt2ts(temp),
                                                                        'avg_val': i * 0.1+0.001}
            result['ts_series'].append(rg_lib.DateTime.dt2ts(temp))

        with open("/home/mathgl/test.xlsx", 'wb') as f:
            sensor_log_report.Make(f, result)
        assert 1





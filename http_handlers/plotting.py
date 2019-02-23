from twisted.internet import defer
from twisted.python import log
from cyclone import web as cyclone_web
from cyclone import escape as c_escape
import datetime
import collections
import functools
import pygal
from pygal import style as pygal_style
import rg_lib
import api_core
import api_sensor_avg_data


def GetValLabel(val, sensor_mdl):
    if val:
        precision = sensor_mdl.get('val_precision')
        template_str = rg_lib.String.PrecisionTemplate(precision) + "{1}"
        return template_str.format(val, sensor_mdl.get('val_unit', ''))
    else:
        return ""


class SensorHourlyLogHandler(cyclone_web.RequestHandler):
    async def __get(self):
        try:
            self.set_header('Content-Type', 'image/svg+xml')
            temp = self.get_argument('sensorids')
            sensorids = c_escape.json_decode(c_escape.url_unescape(temp))
            para = {
                'width': float(self.get_argument('width')),
                'height': float(self.get_argument('height')),
                'hours': int(self.get_argument('hours')),
                'mins': int(self.get_argument('mins')),
                'tz_offset': int(self.get_argument('tz_offset', 0)),
                'sensorids': sensorids
            }
            svg_height = para.get('height')
            svg_width = para.get('width')
            hours = para.get('hours')
            tz_offset = para.get('tz_offset', 0)
            mins = para.get('mins')
            sensorids = para.get('sensorids')
            sql_str = rg_lib.Sqlite.GenInSql(
                """select COALESCE(r1.name,'') name, r1.id, r1.data_no,r1.val_precision, 
                         r1.val_unit from rgw_sensor r1 where r1.id in """,
                sensorids)
            sensors = await api_core.BizDB.Query([sql_str, sensorids])
            sensors_tbl = {s['id']: s for s in sensors}
            curr = rg_lib.DateTime.ts()
            start_ts = curr - hours * 3600
            start_ts = rg_lib.DateTime.dt2ts(rg_lib.DateTime.ts2dt(start_ts).replace(minute=0, second=0))
            dt_series = rg_lib.DateTime.GetMinSeries(start_ts, curr, mins, 'datetime')
            ts_series = [rg_lib.DateTime.dt2ts(i) for i in dt_series]
            rows = await api_sensor_avg_data.QueryMinAvg(start_ts, curr, sensorids, mins, 2000)
            rows_tbl = collections.OrderedDict()
            for r in rows:
                if r['cts'] in rows_tbl:
                    rows_tbl[r['cts']].append(r)
                else:
                    rows_tbl[r['cts']] = [r]
            if len(dt_series) > 9:
                steps = 1 + len(dt_series) // 9
            else:
                steps = 1
            chart_obj = pygal.Line(x_labels_major_every=steps, x_label_rotation=20,
                                   show_minor_x_labels=False, dots_size=1,
                                   height=svg_height, width=svg_width,
                                   legend_at_bottom=True, show_y_guides=False,
                                   y_labels_major_every=3,
                                   show_minor_y_labels=False,
                                   allow_interruptions=True,
                                   style=pygal_style.CleanStyle)
            chart_obj.x_labels = [(rg_lib.DateTime.ts2dt(i) + datetime.timedelta(hours=tz_offset)).strftime('%H:%M')
                                  for i in dt_series]
            for sensorid in sensorids:
                vals = [{'value': None}] * len(chart_obj.x_labels)
                sensor = sensors_tbl[sensorid]
                for _, cts in enumerate(rows_tbl.keys()):
                    for row in rows_tbl[cts]:
                        if row['sensorid'] == sensorid and cts in ts_series:
                            idx = ts_series.index(cts)
                            vals[idx] = {'value': row['avg_val'],
                                         'formatter': functools.partial(GetValLabel, sensor_mdl=sensor)}
                chart_obj.add(sensors_tbl[sensorid]['name'], vals)
            temp = chart_obj.render(True)
            self.finish(temp)
        except Exception:
            log.err()
            raise cyclone_web.HTTPError(400)

    def get(self):
        return defer.ensureDeferred(self.__get())


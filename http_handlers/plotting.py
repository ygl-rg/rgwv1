from twisted.internet import defer
from twisted.python import log
from cyclone import web as cyclone_web
from cyclone import escape as c_escape
import api_plotting as plotting_api


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
            res = await plotting_api.SensorRecentHoursLog(para)
            self.finish(res)
        except Exception:
            log.err()
            raise cyclone_web.HTTPError(400)

    def get(self):
        return defer.ensureDeferred(self.__get())


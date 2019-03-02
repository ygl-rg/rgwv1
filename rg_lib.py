import sys
import sqlite3
import base64
import datetime
import numbers
import math
import calendar
import bson
import pytz
from twisted.internet import defer, protocol
from twisted.python import failure, log
from twisted.enterprise import adbapi
from cyclone import web as cyclone_web
from cyclone import jsonrpc as cyclone_jsonrpc
from cyclone import escape as cyclone_escape


class RGError(Exception):
    def __init__(self, message):
        self.message = message


class ErrorType:
    @classmethod
    def DeclaredType(cls, name):
        return {"declaredType": name, 'msg': ''}

    @classmethod
    def IsErrorType(cls, obj):
        return isinstance(obj, dict) and "declaredType" in obj

    @classmethod
    def NoMethod(cls):
        return cls.DeclaredType("NoMethod")

    @classmethod
    def TypeOfNoMethod(cls, err_obj):
        return cls.IsErrorType(err_obj.message) and err_obj.message['declaredType'] == "NoMethod"

    @classmethod
    def Timeout(cls):
        return cls.DeclaredType("Timeout")

    @classmethod
    def TypeOfTimeout(cls, err_obj):
        return cls.IsErrorType(err_obj.message) and err_obj.message['declaredType'] == "Timeout"

    @classmethod
    def ServerErr(cls, message):
        temp = cls.DeclaredType("ServerErr")
        temp["msg"] = message
        return temp

    @classmethod
    def SqliteIntegrityError(cls):
        return cls.DeclaredType("SqliteIntegrityError")

    @classmethod
    def TypeOfSqliteIntegrityError(cls, err_obj):
        return cls.IsErrorType(err_obj) and err_obj.message['declaredType'] == "SqliteIntegrityError"

    @classmethod
    def ExprError(cls):
        return cls.DeclaredType("ExprError")

    @classmethod
    def TypeOfExprError(cls, err_obj):
        return cls.IsErrorType(err_obj) and err_obj.message['declaredType'] == "ExprError"


class BaseRpcHandler(cyclone_jsonrpc.JsonrpcRequestHandler):
    def _cbResult(self, result, jsonid):
        if isinstance(result, failure.Failure):
            if isinstance(result.value, RGError):
                error = result.value.message
            else:
                error = ErrorType.ServerErr("server error")
            result = None
        elif isinstance(result, AttributeError):
            error = ErrorType.NoMethod()
            result = None
        else:
            error = None
        data = {"result": result, "error": error, "id": jsonid}
        self.finish(cyclone_escape.json_encode(data))


class TempFileHandler(cyclone_web.StaticFileHandler):
    """
    cache file for 60 seconds only
    """

    def get_cache_time(self, path, modified, mime_type):
        return 60


class ExcelFileHandler(cyclone_web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class AsyncDynFuncHandler(BaseRpcHandler):
    def GetFunc(self, func_name):
        raise NotImplementedError()

    def post(self, *args):
        self._auto_finish = False
        try:
            req = cyclone_escape.json_decode(self.request.body)
            jsonid = req["id"]
            method = req["method"]
            assert isinstance(method, str), \
                "Invalid method type: %s" % type(method)
            params = req.get("params", [])
            assert isinstance(params, (list, tuple)), \
                "Invalid params type: %s" % type(params)
        except Exception as e:
            log.msg("Bad Request: %s" % str(e))
            raise cyclone_web.HTTPError(400)

        func = self.GetFunc(method)
        if callable(func):
            args = list(args) + params
            d = defer.ensureDeferred(func(*args))
            d.addBoth(self._cbResult, jsonid)
        else:
            self._cbResult(AttributeError("method not found: %s" % method),
                           jsonid)


class Cyclone:
    @classmethod
    def HandleErr(cls, exc_info_obj):
        log.err(exc_info_obj[1])
        raise exc_info_obj[0].with_traceback(exc_info_obj[1], exc_info_obj[2])

    @classmethod
    def HandleErrInException(cls):
        exc_info_obj = sys.exc_info()
        err_msg = getattr(exc_info_obj[1], "message", None)
        if ErrorType.IsErrorType(err_msg):
            raise RGError(err_msg)
        else:
            cls.HandleErr(exc_info_obj)

    @classmethod
    def TryGetCookie(cls, req_handler, keys):
        for key in keys:
            val = req_handler.get_cookie(key, None)
            if val:
                return val
        else:
            return ''

    @classmethod
    def TryGetRealIp(cls, req_handler):
        if 'X-Forwarded-For' in req_handler.request.headers:
            return req_handler.request.headers['X-Forwarded-For']
        else:
            return req_handler.request.remote_ip

    @classmethod
    def ToTplVal(cls, val):
        return val if val is not None else u"null"

    @classmethod
    def Dir2Url(cls, dir_name):
        temp = dir_name if dir_name[0] == '/' else ('/' + dir_name)
        if temp[-1] != '/':
            temp += '/'
        return temp + '(.*)'


class Sqlite:
    @classmethod
    def SetWalMode(cls, conn_obj):
        conn_obj.execute("PRAGMA journal_mode=WAL")
        conn_obj.execute("PRAGMA synchronous=1")
        conn_obj.execute("PRAGMA cache_size=2000")  # 2000*page_size
        conn_obj.row_factory = sqlite3.Row

    @classmethod
    def SetMemoryMode(cls, conn_obj):
        conn_obj.execute("PRAGMA journal_mode=MEMORY")
        conn_obj.execute("PRAGMA synchronous=0")
        conn_obj.row_factory = sqlite3.Row

    @classmethod
    def SetB64EncodeFunc(cls, conn_obj):
        def __helper(bytes_obj):
            if isinstance(bytes_obj, str):
                temp = bytes_obj.encode('UTF-8')
            else:
                temp = bytes_obj if bytes_obj is not None else b''
            return base64.b64encode(temp)

        conn_obj.create_function('b64encode', 1, __helper)

    @classmethod
    def MakeMemoryConn(cls):
        conn_obj = sqlite3.connect(":memory:", check_same_thread=False)
        cls.SetMemoryMode(conn_obj)
        return conn_obj

    @classmethod
    def MakeConnPool(cls, db_path):
        def __Init(conn_obj):
            cls.SetWalMode(conn_obj)
            cls.SetB64EncodeFunc(conn_obj)

        return adbapi.ConnectionPool("sqlite3", database=db_path, check_same_thread=False,
                                     cp_openfun=__Init, timeout=32)

    @classmethod
    def GenInClause(cls, count):
        return "(" + ",".join(["?" for _ in range(count)]) + ")"

    @classmethod
    def GenInSql(cls, sql_prefix, seq):
        return sql_prefix + cls.GenInClause(len(seq))

    @classmethod
    def FilterArgs(cls, args):
        return [sqlite3.Binary(arg) if isinstance(arg, bson.Binary) else arg for arg in args]

    @classmethod
    def FilterRow(cls, row_obj):
        result = dict(row_obj)
        for key in result:
            if isinstance(result[key], sqlite3.Binary):
                result[key] = bson.Binary(bytes(result[key]))
        return result

    @classmethod
    def CreateTable(cls, table_name, fields, extra_arg=''):
        sql = "CREATE TABLE IF NOT EXISTS {0}".format(table_name)
        sql += '('
        field_str = ',\n'.join([u"{0} {1}".format(i['name'], i['type']) for i in fields])
        sql += field_str
        if len(extra_arg) > 0:
            sql += ',\n' + extra_arg
        sql += ')'
        return sql

    @classmethod
    def RunQuery(cls, conn_pool_obj, sql_rows):
        def __helper(conn_obj):
            conn_obj.execute("BEGIN")
            sql_row = sql_rows[0]
            args = cls.FilterArgs(sql_row[1]) if len(sql_row) > 1 else []
            return [cls.FilterRow(r) for r in conn_obj.execute(sql_row[0], args)]

        return conn_pool_obj.runWithConnection(__helper)

    @classmethod
    def RunInteraction(cls, conn_pool_obj, sql_rows):
        def __helper(conn_obj):
            conn_obj.execute("BEGIN")
            cursor_obj = conn_obj.cursor()
            for sql_row in sql_rows:
                sql_args = cls.FilterArgs(sql_row[1])
                cursor_obj.execute(sql_row[0], sql_args)
            rows = cursor_obj.fetchall()
            cursor_obj.close()
            return [cls.FilterRow(r) for r in rows]

        async def __run():
            try:
                rows = await conn_pool_obj.runWithConnection(__helper)
                return rows
            except sqlite3.IntegrityError:
                raise RGError(ErrorType.SqliteIntegrityError())
            except Exception as e:
                raise e

        return __run()

    @classmethod
    def RunWithConn(cls, conn_pool_obj, func_obj, *args, **kwargs):
        async def __run():
            try:
                res = await conn_pool_obj.runWithConnection(func_obj, *args, **kwargs)
                return res
            except sqlite3.IntegrityError:
                raise RGError(ErrorType.SqliteIntegrityError())
            except Exception as e:
                raise e

        return __run()


class DbConnWrap:
    def __init__(self, conn_obj):
        self.conn_obj = conn_obj

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and exc_val is None and exc_tb is None:
            self.conn_obj.commit()
        else:
            self.conn_obj.rollback()
        self.conn_obj.close()


class TxRedis:
    ACQUIRE_SCRIPT = """
                local res = 0
                if redis.call('exists', KEYS[1]) == 0 then
                    local res_tbl = redis.call('setex', KEYS[1], unpack(ARGV))
                    if (type(res_tbl) == 'table') and (res_tbl["ok"] == "OK") then
                        res = 1
                    end
                end
                return res
            """

    RELEASE_SCRIPT = """
                local res = 0
                if redis.call('exists', KEYS[1]) == 1 then
                    res = redis.call('del', KEYS[1])
                end
                return res
            """

    @classmethod
    def Eval(cls, conn_obj, script, keys=[], args=[]):
        return conn_obj.eval(script, keys=keys, args=args)


class TZ:
    @classmethod
    def GetTimeZoneName(cls, timezone_obj):
        for key in pytz.country_timezones:
            if timezone_obj.zone in pytz.country_timezones[key]:
                return key
        else:
            return "UTC"

    @classmethod
    def GetTimeZone(cls, tz_name):
        if tz_name == "UTC":
            return pytz.timezone(tz_name)
        else:
            return pytz.timezone(pytz.country_timezones[tz_name][0])


class String:
    @classmethod
    def toutf8(cls, text_str):
        if isinstance(text_str, str):
            return text_str.encode('utf-8')
        else:
            return text_str

    @classmethod
    def fromutf8(cls, bytes_str):
        if isinstance(bytes_str, bytes):
            return bytes_str.decode('utf-8')
        else:
            return bytes_str

    @classmethod
    def PrecisionTemplate(cls, precision):
        if isinstance(precision, numbers.Number):
            precision_str = "{0:0." + str(int(precision)) + "f}"
        else:
            precision_str = "{0:0.1f}"
        return precision_str


class DateTime:
    FORMAT1 = r'%Y-%m-%d %H:%M:%S'
    FORMAT2 = r'%Y-%m-%d'
    FORMAT3 = r'%Y-%m-%d %H:%M'
    EPOCH_NAIVE = datetime.datetime.utcfromtimestamp(0)
    DAY_SECONDS = 86400
    DAYS_BETWEEN_1970_1900 = 25569

    @classmethod
    def GetMinSeries(cls, start_dt, stop_dt, mins_interval, dt_format):
        start_dt, stop_dt = cls.ts2dt(start_dt), cls.ts2dt(stop_dt)
        temp, series = start_dt, []
        while temp < stop_dt:
            series.append(temp)
            temp = temp + datetime.timedelta(minutes=mins_interval)
        if dt_format == 'datetime':
            return series
        else:
            return [cls.dt2ts(i) for i in series]

    @classmethod
    def seconds2hhmmss(cls, seconds):
        hour = int(math.floor(seconds / 3600))
        minute = int(math.floor(seconds / 60) % 60)
        second = int(seconds % 60)
        return "{0:02}:{1:02}:{2:02}".format(hour, minute, second)

    @classmethod
    def dt2ts(cls, dt_obj):
        """
        convert datetime to seconds since epoch UTC
        :param dt_obj:
        :return:
        """
        if isinstance(dt_obj, datetime.datetime):
            return calendar.timegm(dt_obj.timetuple())
        elif isinstance(dt_obj, numbers.Number):
            return dt_obj
        else:
            return None

    @classmethod
    def ts2dt(cls, ts_val):
        if isinstance(ts_val, numbers.Number):
            return cls.EPOCH_NAIVE + datetime.timedelta(seconds=ts_val, microseconds=0)
        elif isinstance(ts_val, datetime.datetime):
            return ts_val
        else:
            return None

    @classmethod
    def ts2excel(cls, ts_val):
        int_part = int(ts_val) // cls.DAY_SECONDS + cls.DAYS_BETWEEN_1970_1900
        percentage = 1.0 * (int(ts_val) % cls.DAY_SECONDS) / cls.DAY_SECONDS
        return int_part + percentage

    @classmethod
    def utc(cls, dt_obj=None):
        if dt_obj:
            return dt_obj.replace(microsecond=0, tzinfo=None)
        else:
            return datetime.datetime.utcnow().replace(microsecond=0, tzinfo=None)

    @classmethod
    def DayRangesInMonth(cls, year, month, timezone_obj):
        c = calendar.Calendar(0)
        cursor = c.itermonthdates(year, month)
        offset = timezone_obj.utcoffset(datetime.datetime(year, month, 1, 0, 0, 0))
        result = []
        for rec in cursor:
            if rec.year == year and rec.month == month:
                temp = datetime.datetime(rec.year, rec.month, rec.day, 0, 0, 0)
                local_start = temp.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
                local_stop = temp.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=None)
                result.append({"utc_start": local_start - offset,
                               "utc_stop": local_stop - offset,
                               "local_start": local_start, "local_stop": local_stop})
        return result

    @classmethod
    def ts(cls):
        val = datetime.datetime.utcnow().replace(microsecond=0, tzinfo=None)
        return calendar.timegm(val.timetuple())


class Dict:
    @classmethod
    def DelKeys(cls, tbl, *key_args):
        for k in key_args:
            if k in tbl:
                del tbl[k]
        return tbl


class Collect:
    @classmethod
    def Grouping(cls, seq, predicate_func):
        result = []
        for item in seq:
            if len(result) == 0:
                result.append([item])
            else:
                last_grp = result[-1]
                if predicate_func(item, last_grp[-1]):
                    last_grp.append(item)
                else:
                    result.append([item])
        return result


class Process:
    @classmethod
    def Kill(cls, pid):
        import os
        import signal
        os.kill(int(pid), signal.SIGTERM)


class Twisted:
    @classmethod
    def sleep(cls, seconds):
        from twisted.internet import reactor
        obj = defer.Deferred()
        reactor.callLater(seconds, obj.callback, None)
        return obj


class Locale:
    LOCALES = ["zh-tw", "zh-cn", "en"]

    @classmethod
    def GetLocale(cls, code):
        temp = code.lower().replace("_", "-")
        return temp if temp in cls.LOCALES else "en"


class ProcessProto(protocol.ProcessProtocol):
    def __init__(self, text):
        self.text = text

    def connectionMade(self):
        self.transport.closeStdin()

    def outReceived(self, data):
        pass

    def inReceived(self, data):
        pass


class PageKiteManager(object):
    def __init__(self, pagekite_path='./pagekite.py'):
        self.pid = -1
        self.pagekite_path = String.toutf8(pagekite_path)

    def SetPageKitePath(self, pk_path):
        self.pagekite_path = String.toutf8(pk_path)

    def StartBackend(self, frontend, services):
        """
        :param frontend: string
        :param services: list of string
        :return:
        """
        from twisted.internet import reactor
        tp = ProcessProto('pagekite')
        opts = ["/usr/bin/python2.7", self.pagekite_path, '--clean', '--frontend={0}'.format(frontend),
                '--logfile=/home/pi/pk_secure.log']
        opts += ['--service_on={0}'.format(i) for i in services]
        worker_obj = reactor.spawnProcess(tp, "/usr/bin/python2.7", opts, {})
        self.pid = worker_obj.pid

    def Stop(self):
        if self.pid > 0:
            Process.Kill(self.pid)
            self.pid = -1

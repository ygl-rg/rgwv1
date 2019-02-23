# -*- coding: utf-8 -*-
import numbers
import apscheduler.util as aps_util
import json
import bson
import datetime
import pytz
import rg_lib
import rgw_consts


class NoRightError(rg_lib.RGError):
    def __init__(self):
        rg_lib.RGError.__init__(self, 'no right')


class AccessOverLimit(rg_lib.RGError):
    def __init__(self):
        rg_lib.RGError.__init__(self, 'access over limit')


class PasswordError(rg_lib.RGError):
    def __init__(self):
        rg_lib.RGError.__init__(self, 'password error')


class ErrorTypes:
    @classmethod
    def UnsupportedOp(cls):
        return rg_lib.ErrorType.DeclaredType("UnsupportedOp")


class UserSession:
    @classmethod
    def make(cls, pwd):
        new_id = bson.ObjectId()
        res = {"sessionid": str(new_id), 'pwd': pwd}
        curr_time = rg_lib.DateTime.utc(new_id.generation_time)
        res['expiry'] = rg_lib.DateTime.dt2ts(
            curr_time + datetime.timedelta(seconds=rgw_consts.Timeout.COOKIE_INTERVAL))
        return res, curr_time


class SwitchSchedule:
    TBL1 = "rgw_switch_schedule"

    TBL1_FIELDS = [
        {'name': 'id', 'type': 'varchar(64) not null primary key'},
        {'name': 'local_start_time', 'type': 'varchar(64) not null'},
        {'name': 'local_stop_time', 'type': 'varchar(64) not null'},
        {'name': 'start_ts', 'type': 'datetime not null'},
        {'name': 'stop_ts', 'type': 'datetime not null'},
        {'name': 'hour', 'type': 'integer'},
        {'name': 'minute', 'type': 'integer'},
        {'name': 'second', 'type': 'integer'},
        {'name': 'prev_run_ts', 'type': 'datetime'},
        {'name': 'next_run_ts', 'type': 'datetime'},
        {'name': 'next_run_until_ts', 'type': 'datetime'},
        {'name': 'local_next_run_time', 'type': 'varchar(64)'},
        {'name': 'action_no', 'type': 'varchar(64) not null'},
        {'name': 'timezone', 'type': 'varchar(64) not null'},
        {'name': 'working_seconds', 'type': 'integer'},
    ]

    TBL2 = 'rgw_switch_schedule_switch'

    TBL2_FIELDS = [
        {'name': 'scheduleid', 'type': 'varchar(64) not null'},
        {'name': 'switchid', 'type': 'varchar(64) not null'}
    ]

    IDX1 = """
    create index if not exists rgw_switch_schedule_idx1 on rgw_switch_schedule(next_run_ts)
    """

    IDX2 = """
    create index if not exists rgw_switch_schedule_idx2 on rgw_switch_schedule(stop_ts)
    """

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL1, cls.TBL1_FIELDS))
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL2, cls.TBL2_FIELDS,
                                                   'primary key(scheduleid, switchid)'))
        conn_obj.execute(cls.IDX1)
        conn_obj.execute(cls.IDX2)

    @classmethod
    def GenId(cls):
        return str(bson.ObjectId())

    @classmethod
    def UpdateTsRange(cls, schedule_mdl):
        local_start_dt, local_stop_dt = cls.GetLocalDtRange(schedule_mdl)
        schedule_mdl['start_ts'] = rg_lib.DateTime.dt2ts(local_start_dt - local_start_dt.utcoffset())
        schedule_mdl['stop_ts'] = rg_lib.DateTime.dt2ts(local_stop_dt - local_stop_dt.utcoffset())
        return schedule_mdl

    @classmethod
    def GetLocalDtRange(cls, schedule_mdl):
        local_start, local_stop = None, None
        if 'timezone' in schedule_mdl:
            tz_obj = pytz.timezone(schedule_mdl['timezone'])
            if 'local_start_time' in schedule_mdl:
                local_start = aps_util.convert_to_datetime(schedule_mdl['local_start_time'], tz_obj, '')
            if 'local_stop_time' in schedule_mdl:
                local_stop = aps_util.convert_to_datetime(schedule_mdl['local_stop_time'], tz_obj, '').replace(hour=23, minute=59, second=59)
        return local_start, local_stop

    @classmethod
    def make(cls, scheduleid, action_no, switchids, local_start_time, local_stop_time,
             hour, minute, second, timezone,
             working_seconds):
        mdl = {"id": scheduleid, 'action_no': action_no, 'switchids': switchids,
               'prev_run_ts': None,
               'local_start_time': local_start_time,
               'local_stop_time': local_stop_time,
               'hour': hour, 'minute': minute, 'second': second,
               'timezone': timezone, 'working_seconds': working_seconds}
        cls.UpdateTsRange(mdl)
        ts_tbl = cls.ComputeNextRunTs(mdl)
        mdl.update(ts_tbl)
        return mdl

    @classmethod
    def ComputeWorkingSecs(cls, schedule_mdl):
        if (schedule_mdl['next_run_ts'] + schedule_mdl['working_seconds']) > (schedule_mdl['stop_ts']+1):
            return schedule_mdl['stop_ts'] - schedule_mdl['next_run_ts']
        else:
            return schedule_mdl['working_seconds']

    @classmethod
    def ComputeNextRunTs(cls, schedule_mdl):
        """
        :param schedule_mdl:
        :return: {"next_run_ts", "local_next_run_time", "next_run_until_ts"}
        """
        local_start, local_stop = cls.GetLocalDtRange(schedule_mdl)
        tz_obj = pytz.timezone(schedule_mdl['timezone'])
        local_now = datetime.datetime.now(tz_obj).replace(microsecond=0)
        maybe_start = max(local_start, local_now)
        if schedule_mdl.get('next_run_ts', None):
            local_next_start = tz_obj.fromutc(rg_lib.DateTime.ts2dt(schedule_mdl['next_run_ts'])) + datetime.timedelta(seconds=1)
            maybe_start = max(local_next_start, maybe_start)
        maybe_next = maybe_start.replace(hour=schedule_mdl['hour'], minute=schedule_mdl['minute'],
                                         second=schedule_mdl['second'])
        if maybe_start > maybe_next:
            local_next_fire = maybe_next + datetime.timedelta(days=1)
        else:
            local_next_fire = maybe_next
        if local_next_fire > local_stop:
            local_next_fire = None
        if local_next_fire:
            temp = local_next_fire - local_now.utcoffset()
            next_run_dt = datetime.datetime.combine(temp.date(), temp.time())
            return {'next_run_ts': rg_lib.DateTime.dt2ts(next_run_dt),
                    'next_run_until_ts': rg_lib.DateTime.dt2ts(next_run_dt + datetime.timedelta(seconds=schedule_mdl['working_seconds'])),
                    'local_next_run_time': local_next_fire.strftime(rg_lib.DateTime.FORMAT1)}
        else:
            return {'next_run_ts': None, 'next_run_until_ts': None, 'local_next_run_time': ''}

    @classmethod
    def BeforeSet(cls, schedule_mdl):
        cls.UpdateTsRange(schedule_mdl)
        return rg_lib.Dict.DelKeys(schedule_mdl, 'next_run_ts')

    @classmethod
    def PartialUpdate(cls, mdl, excludes):
        """
        only return set parts, need to attach where clause
        :param mdl:
        :param excludes list of excluded keys
        :return: [partial sql, args]
        """
        terms = []
        args = []
        for key in mdl:
            if key not in excludes:
                terms.append("{0}=?".format(key))
                args.append(mdl[key])
        update_sql = "update rgw_switch_schedule set "
        update_sql += ",".join(terms)
        update_sql += " where "
        return [update_sql, args]

    @classmethod
    def DynInsert(cls, rec_tbl, ignored=False):
        """
        :param rec_tbl:
        :param ignored:
        :return: sql_rows
        """
        sql_rows = []
        terms = []
        args = []
        marks = []
        for key in rec_tbl:
            if key != 'switchids':
                terms.append(key)
                marks.append("?")
                args.append(rec_tbl[key])

        if ignored:
            insert_sql = "insert or ignore into rgw_switch_schedule("
        else:
            insert_sql = "insert into rgw_switch_schedule("
        insert_sql += ",".join(terms)
        insert_sql += ") values ("
        insert_sql += ",".join(marks)
        insert_sql += ")"
        sql_rows.append([insert_sql, args])
        if isinstance(rec_tbl['switchids'] if 'switchids' in rec_tbl else None, list):
            for devid in rec_tbl['switchids']:
                if ignored:
                    sql_rows.append(
                        ["insert or ignore into rgw_switch_schedule_switch values(?,?)",
                         (rec_tbl['id'], devid)]
                    )
                else:
                    sql_rows.append(
                        ["insert into rgw_switch_schedule_switch values(?,?)",
                         (rec_tbl['id'], devid)]
                    )
        return sql_rows


class SwitchAction:
    ON = "ON"
    OFF = "OFF"
    OP_SUCC = 1
    OP_FAIL = 0

    TBL = "rgw_switch_action"

    TBL_FIELDS = [
        {'name': 'switchid', 'type': 'varchar(64) primary key'},
        {'name': 'start_ts', 'type': 'datetime not null'},
        {'name': 'stop_ts', 'type': 'datetime not null'},
        {'name': 'next_run_ts', 'type': 'datetime'},
        {'name': 'working_seconds', 'type': 'integer not null default 0'},
        {'name': 'op_status', 'type': 'integer not null default 0'}
    ]

    IDX1 = """
    create index if not exists rgw_switch_action_idx2 on rgw_switch_action(stop_ts)
    """

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL, cls.TBL_FIELDS))
        conn_obj.execute(cls.IDX1)

    @classmethod
    def make(cls, switchid, start_ts, stop_ts, working_seconds):
        return {'switchid': switchid,
                'start_ts': start_ts,
                'stop_ts': stop_ts,
                'next_run_ts': start_ts,
                'working_seconds': working_seconds}

    @classmethod
    def DynInsert(cls, rec_tbl, ignored=False):
        terms = []
        args = []
        marks = []
        for key in rec_tbl:
            terms.append(key)
            marks.append("?")
            args.append(rec_tbl[key])

        if ignored:
            insert_sql = "insert or ignore into rgw_switch_action("
        else:
            insert_sql = "insert into rgw_switch_action("
        insert_sql += ",".join(terms)
        insert_sql += ") values ("
        insert_sql += ",".join(marks)
        insert_sql += ")"
        return [insert_sql, args]

    @classmethod
    def UpdateExistingAction(cls, action_mdl):
        sql = """update or ignore rgw_switch_action 
                  set stop_ts=?, working_seconds=?
                  where switchid=? and stop_ts<?"""
        sql_args = [action_mdl['stop_ts'], action_mdl['working_seconds'],
                    action_mdl['switchid'], action_mdl['stop_ts']]
        return [sql, sql_args]


class MultiText:
    @classmethod
    def GetValue(cls, text, lang='en'):
        if lang != 'en':
            if lang in text:
                return text[lang]
            else:
                return text.get('en')
        else:
            return text.get('en')


class Switch:
    OFF = "OFF"
    ON = "ON"

    TBL = 'rgw_switch'

    TBL_FIELDS = [
        {'name': 'id', 'type': 'varchar(64) primary key'},
        {'name': 'name', 'type': "varchar(128) not null default ''"},
        {'name': 'remark', 'type': 'text'},
        {'name': 'iconid', 'type': "text not null default ''"},
        {'name': 'tag', 'type': "text not null default ''"},
        {'name': 'uts', 'type': "datetime"}
    ]

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL, cls.TBL_FIELDS))

    @classmethod
    def SqlRows_Remove(cls, switchids):
        sqls = []
        switchids = switchids if isinstance(switchids, list) else [switchids]
        for sensorid in switchids:
            sqls.append(["delete from rgw_switch where id=?", (sensorid,)])
        return sqls

    @classmethod
    def make(cls, deviceid, name):
        return {"id": deviceid, "name": name}

    @classmethod
    def DynUpdate(cls, mdl):
        """
        :param mdl: switch model
        :return: [sql, sql_args]
        """
        terms = []
        args = []
        for key in mdl:
            if key not in ('id',):
                terms.append("{0}=?".format(key))
                args.append(mdl[key])
        update_sql = "update rgw_switch set "
        update_sql += ",".join(terms)
        update_sql += " where id=?"
        args.append(mdl['id'])
        return [update_sql, args]

    @classmethod
    def DynInsert(cls, rec_tbl, ignored=False):
        terms = []
        args = []
        marks = []
        for key in rec_tbl:
            terms.append(key)
            marks.append("?")
            args.append(rec_tbl[key])

        if ignored:
            insert_sql = "insert or ignore into rgw_switch("
        else:
            insert_sql = "insert into rgw_switch("
        insert_sql += ",".join(terms)
        insert_sql += ") values ("
        insert_sql += ",".join(marks)
        insert_sql += ")"
        return [insert_sql, args]


class SwitchOpSession:
    TBL = "rgw_switch_op_session"

    TBL_FIELDS = [
        {'name': 'switchid', 'type': 'varchar(64) primary key'},
        {'name': 'status', 'type': 'text not null'},
        {'name': 'uts', 'type': 'datetime not null'}
    ]

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL, cls.TBL_FIELDS))

    @classmethod
    def Make(cls, switchid, uts, status):
        return {'switchid': switchid, 'uts': uts, 'status': status}


class SwitchOpDuration:
    TBL = "rgw_switch_op_duration"

    TBL_FIELDS = [
        {'name': 'switchid', 'type': 'varchar(64) not null'},
        {'name': 'start_ts', 'type': 'datetime not null'},
        {'name': 'stop_ts', 'type': 'datetime not null'},
        {'name': 'status', 'type': 'text not null'},
        {'name': 'val', 'type': 'integer not null'}
    ]

    IDX1 = """create unique index if not exists rgw_switch_op_duration_idx1 on rgw_switch_op_duration(switchid, stop_ts, status)"""

    IDX2 = """create unique index if not exists rgw_switch_op_duration_idx2 on rgw_switch_op_duration(switchid, start_ts, status)"""

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL, cls.TBL_FIELDS))
        conn_obj.execute(cls.IDX1)
        conn_obj.execute(cls.IDX2)

    @classmethod
    def DynInsert(cls, mdl, ignored=False):
        terms = []
        args = []
        marks = []
        for key in mdl:
            terms.append(key)
            marks.append("?")
            args.append(mdl[key])
        if ignored:
            insert_sql = "insert or ignore into rgw_switch_op_duration("
        else:
            insert_sql = "insert into rgw_switch_op_duration("
        insert_sql += ",".join(terms)
        insert_sql += ") values ("
        insert_sql += ",".join(marks)
        insert_sql += ")"
        return [insert_sql, args]

    @classmethod
    def make(cls, start_ts, stop_ts, switchid, status, val):
        return {'switchid': switchid,
                'start_ts': rg_lib.DateTime.dt2ts(start_ts),
                'stop_ts': rg_lib.DateTime.dt2ts(stop_ts),
                'status': status, 'val': val}


class SysCfg:
    KEYS = ['timezone', 'pagekite_path', 'pagekite_frontend', 'domain', 'pagekite_pwd',
            'pwd', 'gw_url', 'email_sender',
            'elasticemail_api_key', 'elasticemail_send_url']

    TBL = "rgw_sys_cfg"

    TBL_FIELDS = [
        {'name': 'key', 'type': 'text not null'},
        {'name': 'val', 'type': 'text not null'}
    ]

    IDX1 = "create unique index if not exists rgw_sys_cfg_idx1 on rgw_sys_cfg(key)"

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL, cls.TBL_FIELDS))
        conn_obj.execute(cls.IDX1)

    @classmethod
    def SqlRows_Remove(cls, keys):
        sqls = []
        keys = keys if isinstance(keys, list) else []
        for key in keys:
            sqls.append(["delete from rgw_sys_cfg where key=?", (key,)])
        return sqls

    @classmethod
    def Filter(cls, mdl):
        return {k: mdl[k] for k in mdl if k in cls.KEYS}

    @classmethod
    def DynUpdate(cls, mdl, ignore=False):
        """
        :param mdl:
        :param ignore:
        :return: sql_rows
        """
        sql_rows = []
        items = [{'key': i, 'val': mdl[i]} for i in mdl]
        for item in items:
            if ignore:
                update_sql = "update or ignore rgw_sys_cfg set val=?"
            else:
                update_sql = "update rgw_sys_cfg set val=?"
            update_sql += " where key=?"
            sql_rows.append([update_sql, (item['val'], item['key'])])
        return sql_rows

    @classmethod
    def DynInsert(cls, rec_tbl, ignore=False):
        sql_rows = []
        items = [{'key': i, 'val': rec_tbl[i]} for i in rec_tbl]
        for item in items:
            if ignore:
                insert_sql = "insert or ignore into rgw_sys_cfg(key,val) values(?,?)"
            else:
                insert_sql = "insert into rgw_sys_cfg(key,val) values(?,?)"
            sql_rows.append([insert_sql, (item['key'], item['val'])])
        return sql_rows

    @classmethod
    def DynUpsert(cls, mdl):
        sql_rows = []
        sql_rows.extend(cls.DynInsert(mdl, True))
        sql_rows.extend(cls.DynUpdate(mdl, True))
        return sql_rows


class Sensor:
    TBL = 'rgw_sensor'

    TBL_FIELDS = [
        {'name': 'id', 'type': 'varchar(64) primary key'},
        {'name': 'deviceid', 'type': 'varchar(64) not null'},
        {'name': 'val_offset', 'type': 'integer not null default 0'},
        {'name': 'data_no', 'type': 'varchar(64) not null'},
        {'name': 'name', 'type': "varchar(128) not null default ''"},
        {'name': 'val', 'type': 'double'},
        {'name': 'val_unit', 'type': "varchar(64) not null default ''"},
        {'name': 'val_precision', 'type': 'integer not null default 1'},
        {'name': 'remark', 'type': 'text'},
        {'name': 'extra_arg0', 'type': 'double'},
        {'name': 'func_body', 'type': "text not null default ''"},
        {'name': 'uts', 'type': 'datetime'},
        {'name': 'iconid', 'type': "text not null default ''"},
        {'name': 'tag', 'type': "text not null default ''"}
    ]

    IDX1 = "create index if not exists rgw_sensor_idx1 on rgw_sensor(deviceid)"

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL, cls.TBL_FIELDS))
        conn_obj.execute(cls.IDX1)

    @classmethod
    def SqlRows_Remove(cls, sensorids):
        sqls = []
        sensorids = sensorids if isinstance(sensorids, list) else [sensorids]
        for sensorid in sensorids:
            sqls.append(["delete from rgw_sensor where id=?", (sensorid,)])
        return sqls

    @classmethod
    def make(cls, deviceid, val_offset, data_no, name):
        return {"deviceid": deviceid, "val_offset": val_offset,
                "data_no": data_no,
                "name": name,
                'id': Sensor.GenId(deviceid, val_offset)}

    @classmethod
    def GenId(cls, deviceid, offset):
        return "{0}_{1}".format(deviceid, offset)

    @classmethod
    def GenId2(cls, sensor):
        return cls.GenId(sensor['deviceid'], sensor['val_offset'])

    @classmethod
    def ExtractDeviceId(cls, sensorids):
        if isinstance(sensorids, list):
            id_set = set()
            for sid in sensorids:
                stop = sid.find('_')
                if stop > 15:
                    id_set.add(sid[0:stop])
            return list(id_set)
        else:
            stop = sensorids.find('_')
            if stop > 15:
                return sensorids[0:stop]
            else:
                return ''

    @classmethod
    def BeforeAdd(cls, sensor):
        sensor['id'] = cls.GenId2(sensor)
        return rg_lib.Dict.DelKeys(sensor, 'val', 'network_status')

    @classmethod
    def BeforeSet(cls, sensor):
        return rg_lib.Dict.DelKeys(sensor, 'val', 'uts', 'deviceid', 'val_offset', 'network_status')

    @classmethod
    def DynUpdate(cls, mdl, is_ignored):
        terms = []
        args = []
        for key in mdl:
            if key != 'id':
                terms.append("{0}=?".format(key))
                args.append(mdl[key])
        if is_ignored:
            update_sql = "update or ignore rgw_sensor set"
        else:
            update_sql = "update rgw_sensor set "
        update_sql += ",".join(terms)
        update_sql += " where id=?"
        args.append(mdl['id'])
        return [update_sql, args]

    @classmethod
    def DynInsert(cls, rec_tbl, is_ignored):
        terms = []
        args = []
        marks = []
        for key in rec_tbl:
            if rec_tbl[key] is not None:
                terms.append(key)
                marks.append("?")
                args.append(rec_tbl[key])
        if is_ignored:
            insert_sql = "insert or ignore into rgw_sensor("
        else:
            insert_sql = "insert into rgw_sensor("
        insert_sql += ",".join(terms)
        insert_sql += ") values ("
        insert_sql += ",".join(marks)
        insert_sql += ")"
        return [insert_sql, args]

    @classmethod
    def HasFuncBody(cls, sensor):
        if sensor is None:
            return False
        if 'func_body' in sensor:
            if isinstance(sensor['func_body'], str):
                return len(sensor['func_body']) > 5
            else:
                return False
        else:
            return False

    @classmethod
    def HasExtraArg0(cls, sensor_mdl):
        if sensor_mdl is None:
            return False
        if 'extra_arg0' in sensor_mdl:
            return isinstance(sensor_mdl['extra_arg0'], numbers.Number)
        else:
            return False

    @classmethod
    def FromRow(cls, row):
        if 'uts' in row:
            if (row['uts'] is None) or row['uts'] < (rg_lib.DateTime.ts() - 90):
                row['network_status'] = rgw_consts.Network.OFFLINE
            else:
                row['network_status'] = rgw_consts.Network.ONLINE
        return row


class SensorData:
    FIELDS = ['cts', 'sensorid', 'data_no', 'val']

    TBL = "rgw_sensor_data"

    TBL_FIELDS = [
        {'name': 'sensorid', 'type': 'varchar(64) not null'},
        {'name': 'cts', 'type': 'datetime not null'},
        {'name': 'data_no', 'type': 'varchar(64) not null'},
        {'name': 'val', 'type': 'double not null'},
    ]

    IDX1 = """create index if not exists rgw_sensor_data_idx1 on rgw_sensor_data(cts)"""

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL, cls.TBL_FIELDS,
                                                   'PRIMARY key(sensorid, cts)'))
        conn_obj.execute(cls.IDX1)

    @classmethod
    def make(cls, ts):
        return {'cts': ts, 'val': None}

    @classmethod
    def Sync(cls, sensor_mdl):
        tbl = cls.make(sensor_mdl['uts'])
        for k in cls.FIELDS:
            if k in sensor_mdl:
                tbl[k] = sensor_mdl[k]
        if 'id' in sensor_mdl:
            tbl['sensorid'] = sensor_mdl['id']
        return tbl

    @classmethod
    def DynInsert(cls, rec_tbl, ignored=False):
        terms = []
        args = []
        marks = []
        for key in rec_tbl:
            terms.append(key)
            marks.append("?")
            args.append(rec_tbl[key])
        if ignored:
            insert_sql = "insert or ignore into rgw_sensor_data("
        else:
            insert_sql = "insert into rgw_sensor_data("
        insert_sql += ",".join(terms)
        insert_sql += ") values ("
        insert_sql += ",".join(marks)
        insert_sql += ")"
        return [insert_sql, args]


class SensorTrigger:
    TBL1 = "rgw_sensor_trigger"

    TBL1_FIELDS = [
        {'name': 'id', 'type': 'integer primary key'},
        {'name': 'name', 'type': "text not null default ''"},
        {'name': 'start_ts', 'type': 'integer not null default 0'},
        {'name': 'stop_ts', 'type': 'integer not null default 0'},
        {'name': 'check_interval', 'type': 'integer not null default 30'},
        {'name': 'emails', 'type': "text not null default '[]'"},
        {'name': 'message', 'type': "text not null default ''"}
    ]

    TBL2 = "rgw_sensor_trigger_sensor"

    TBL2_FIELDS = [
        {'name': 'triggerid', 'type': 'integer not null'},
        {'name': 'sensorid', 'type': 'varchar(64) not null'},
        {'name': 'op', 'type': 'text not null'},
        {'name': 'rval', 'type': 'text not null'}
    ]

    TBL3 = "rgw_sensor_trigger_switch"

    TBL3_FIELDS = [
        {'name': 'triggerid', 'type': 'integer not null'},
        {'name': 'switchid', 'type': 'varchar(64) not null'},
        {'name': 'action_no', 'type': 'varchar(64) not null'},
        {'name': 'working_seconds', 'type': 'integer'}
    ]

    IDX1 = """
    create unique index if not exists rgw_sensor_trigger_idx1 on rgw_sensor_trigger(name)
    """

    IDX2 = """
    create index if not exists rgw_sensor_trigger_idx2 on rgw_sensor_trigger_sensor(sensorid)
    """

    IDX3 = """
    create index if not exists rgw_sensor_trigger_idx3 on rgw_sensor_trigger_switch(switchid)
    """

    IDX4 = """
    create index if not exists rgw_sensor_trigger_idx4 on rgw_sensor_trigger(start_ts)
    """

    IDX5 = """
    create index if not exists rgw_sensor_trigger_idx5 on rgw_sensor_trigger(stop_ts)
    """

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL1, cls.TBL1_FIELDS))
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL2, cls.TBL2_FIELDS, "primary key(triggerid, sensorid)"))
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL3, cls.TBL3_FIELDS, "primary key(triggerid, switchid)"))
        conn_obj.execute(cls.IDX1)
        conn_obj.execute(cls.IDX2)
        conn_obj.execute(cls.IDX3)
        conn_obj.execute(cls.IDX4)
        conn_obj.execute(cls.IDX5)

    @classmethod
    def HasId(cls, mdl):
        if 'id' in mdl:
            return mdl['id'] > 0
        else:
            return False

    @classmethod
    def BeforeAdd(cls, mdl):
        return rg_lib.Dict.DelKeys(mdl, 'id', 'rowid')

    @classmethod
    def BeforeSet(cls, mdl):
        return rg_lib.Dict.DelKeys(mdl, 'rowid')

    @classmethod
    def DynUpdate(cls, mdl, ignored=False):
        terms = []
        args = []
        for key in mdl:
            if key != 'id':
                terms.append("{0}=?".format(key))
                if key == 'emails':
                    args.append(json.dumps(mdl[key]))
                else:
                    args.append(mdl[key])
        if ignored:
            update_sql = "update or ignore rgw_sensor_trigger set "
        else:
            update_sql = "update rgw_sensor_trigger set "
        update_sql += ",".join(terms)
        update_sql += " where id=?"
        args.append(mdl['id'])
        return [update_sql, args]

    @classmethod
    def DynInsert(cls, rec_tbl, ignored=False):
        terms = []
        args = []
        marks = []
        for key in rec_tbl:
            terms.append(key)
            marks.append("?")
            if key == 'emails':
                args.append(json.dumps(rec_tbl[key]))
            else:
                args.append(rec_tbl[key])
        if ignored:
            insert_sql = "insert or ignore into rgw_sensor_trigger("
        else:
            insert_sql = "insert into rgw_sensor_trigger("
        insert_sql += ",".join(terms)
        insert_sql += ") values ("
        insert_sql += ",".join(marks)
        insert_sql += ")"
        return [insert_sql, args]

    @classmethod
    def GenExpr(cls, op):
        return "(? {0} ?)".format(op)

    @classmethod
    def GenAndExpr(cls, terms):
        """
        :param terms: [(op, lval, rval),...]
        :return: sql, sql_args
        """
        sql = " and ".join([cls.GenExpr(term[0]) for term in terms])
        sql_args = []
        for term in terms:
            sql_args.append(term[1])
            try:
                sql_args.append(float(term[2]))
            except ValueError:
                sql_args.append(term[2])
        return sql, sql_args

    @classmethod
    def FromRow(cls, row):
        if 'emails' in row:
            row['emails'] = json.loads(row['emails'])
        return row


class XYDevice:
    @classmethod
    def HasVals(cls, mdl):
        return (mdl is not None) and isinstance(mdl.get('vals', None), list)

    @classmethod
    def ValsNotEmpty(cls, mdl):
        return cls.HasVals(mdl) and len(mdl['vals']) > 0


class TriggerLog:
    FIELDS = ['cts', 'triggerid', 'message']

    TBL = "rgw_trigger_log"

    TBL_FIELDS = [
        {'name': 'triggerid', 'type': 'integer not null'},
        {'name': 'cts', 'type': 'datetime not null'},
        {'name': 'message', 'type': 'text not null'}
    ]

    IDX1 = """create index if not exists rgw_trigger_log_idx1 on rgw_trigger_log(cts)"""

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL, cls.TBL_FIELDS,
                                                   'PRIMARY key(triggerid, cts)'))
        conn_obj.execute(cls.IDX1)

    @classmethod
    def make(cls, ts, triggerid, message):
        return {'cts': ts, 'triggerid': triggerid, 'message': message}

    @classmethod
    def DynInsert(cls, rec_tbl, ignored=False):
        terms = []
        args = []
        marks = []
        for key in rec_tbl:
            terms.append(key)
            marks.append("?")
            args.append(rec_tbl[key])
        if ignored:
            insert_sql = "insert or ignore into rgw_trigger_log("
        else:
            insert_sql = "insert into rgw_trigger_log("
        insert_sql += ",".join(terms)
        insert_sql += ") values ("
        insert_sql += ",".join(marks)
        insert_sql += ")"
        return [insert_sql, args]


class SensorAvgData:
    FIELDS = ['cts', 'sensorid', 'data_no', 'val']

    TBL = "rgw_sensor_avg_data"

    TBL_FIELDS = [
        {'name': 'sensorid', 'type': 'varchar(64) not null'},
        {'name': 'cts', 'type': 'datetime not null'},
        {'name': 'data_no', 'type': 'varchar(64) not null'},
        {'name': 'val', 'type': 'double not null'},
    ]

    IDX1 = """create index if not exists rgw_sensor_avg_data_idx1 on rgw_sensor_avg_data(cts)"""

    @classmethod
    def Init(cls, conn_obj):
        conn_obj.execute(rg_lib.Sqlite.CreateTable(cls.TBL, cls.TBL_FIELDS,
                                                   'PRIMARY key(sensorid, cts)'))
        conn_obj.execute(cls.IDX1)

    @classmethod
    def make(cls, ts):
        return {'cts': ts, 'val': None}

    @classmethod
    def Sync(cls, sensor_data):
        tbl = cls.make(sensor_data['cts'])
        for k in cls.FIELDS:
            if k in sensor_data:
                tbl[k] = sensor_data[k]
        if 'avg_val' in sensor_data:
            tbl['val'] = sensor_data['avg_val']
        return tbl

    @classmethod
    def DynInsert(cls, rec_tbl, ignored=False):
        terms = []
        args = []
        marks = []
        for key in rec_tbl:
            terms.append(key)
            marks.append("?")
            args.append(rec_tbl[key])
        if ignored:
            insert_sql = "insert or ignore into rgw_sensor_avg_data("
        else:
            insert_sql = "insert into rgw_sensor_avg_data("
        insert_sql += ",".join(terms)
        insert_sql += ") values ("
        insert_sql += ",".join(marks)
        insert_sql += ")"
        return [insert_sql, args]

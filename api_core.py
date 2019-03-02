from twisted.python import log
from twisted.internet import defer, error
import txredisapi
import treq
import rg_lib
import settings
import models
import rgw_consts


class BizDB:
    db_pool = None
    redis_conn = None

    @classmethod
    async def Query(cls, sql_row):
        """
        :param sql_row: [sql, args]
        :return: rows
        """
        return await rg_lib.Sqlite.RunQuery(cls.db_pool, [sql_row])

    @classmethod
    async def Get(cls, sql_row):
        rows = await cls.Query(sql_row)
        return rows[0] if len(rows) > 0 else None

    @classmethod
    def Interaction(cls, sql_rows):
        return rg_lib.Sqlite.RunInteraction(cls.db_pool, sql_rows)

    @classmethod
    def Init(cls):
        def helper(conn_obj):
            conn_obj.execute("BEGIN")
            models.SysCfg.Init(conn_obj)
            models.Sensor.Init(conn_obj)
            models.SensorTrigger.Init(conn_obj)
            models.Switch.Init(conn_obj)
            models.SwitchSchedule.Init(conn_obj)
            models.SwitchAction.Init(conn_obj)

        cls.db_pool = rg_lib.Sqlite.MakeConnPool(settings.BIZ_DB['path'])
        cls.redis_conn = txredisapi.lazyConnectionPool(host=settings.REDIS['host'],
                                                       port=settings.REDIS['port'],
                                                       charset=None,
                                                       convertNumbers=False)
        return cls.db_pool.runWithConnection(helper)

    @classmethod
    def Close(cls):
        if cls.db_pool:
            cls.db_pool.close()
            cls.db_pool = None
        if cls.redis_conn:
            cls.redis_conn.quit()
            cls.redis_conn = None


class LogDB:
    db_pool = None

    @classmethod
    def Interaction(cls, sql_rows):
        return rg_lib.Sqlite.RunInteraction(cls.db_pool, sql_rows)

    @classmethod
    async def Query(cls, sql_row):
        """
        :param sql_row: [sql, args]
        :return: list of dict
        """
        return await rg_lib.Sqlite.RunQuery(cls.db_pool, [sql_row])

    @classmethod
    def Init(cls):
        def helper(conn_obj):
            conn_obj.execute("BEGIN")
            models.SensorData.Init(conn_obj)
            models.SwitchOpDuration.Init(conn_obj)
            models.TriggerLog.Init(conn_obj)
            models.SensorAvgData.Init(conn_obj)

        cls.db_pool = rg_lib.Sqlite.MakeConnPool(settings.LOG_DB['path'])
        return cls.db_pool.runWithConnection(helper)

    @classmethod
    def Close(cls):
        if cls.db_pool:
            cls.db_pool.close()
            cls.db_pool = None


class Sensor:
    @classmethod
    async def Add(cls, sensor_tbl):
        mdl = models.Sensor.BeforeAdd(sensor_tbl)
        await BizDB.Interaction([models.Sensor.DynInsert(mdl, False)])
        return mdl['id']

    @classmethod
    def Update(cls, sensor_tbl):
        mdl = models.Sensor.BeforeSet(sensor_tbl)
        return BizDB.Interaction([models.Sensor.DynUpdate(mdl, False)])

    @classmethod
    def Remove(cls, sensorids):
        return BizDB.Interaction(models.Sensor.SqlRows_Remove(sensorids))

    @classmethod
    async def Query(cls, sql_row):
        """
        :param sql_row: [sql, args]
        :return: models.Sensor
        """
        rows = await BizDB.Query(sql_row)
        return [models.Sensor.FromRow(r) for r in rows]

    @classmethod
    async def Get(cls, sql_row):
        rows = await cls.Query(sql_row)
        return rows[0] if rows else None

    @classmethod
    def ById(cls, sensorid):
        return cls.Get(["""select r1.* from rgw_sensor r1 where r1.id=?""", (sensorid,)])

    @classmethod
    def SqlRows_UpdateVal(cls, sensors):
        return [["update rgw_sensor set val=?, uts=? where id=?", (i['val'], i['uts'], i['id'])] for i in sensors]

    @classmethod
    def UpdateVal(cls, sensors):
        return BizDB.Interaction(cls.SqlRows_UpdateVal(sensors))

    @classmethod
    def UpdateName(cls, sensorid, name, tag):
        sql_str = """update rgw_sensor set name=?, tag=? where id=?"""
        sql_args = [name, tag, sensorid]
        return BizDB.Interaction([[sql_str, sql_args]])

    @classmethod
    def Search(cls, para):

        """
        :param para: {"name", "val"}
        :return: [cfg,...]
        """
        if para['name'] == "name":
            sql_str = """select r1.* from rgw_sensor r1 where r1.name like ? limit ?"""
        else:
            raise rg_lib.RGError(models.ErrorTypes.UnsupportedOp())
        sql_args = ("{0}%".format(para['val']), rgw_consts.DbConsts.SEARCH_LIMIT)
        return cls.Query([sql_str, sql_args])


class Switch:
    @classmethod
    def Add(cls, switch_mdl):
        return BizDB.Interaction([models.Switch.DynInsert(switch_mdl)])

    @classmethod
    def Update(cls, switch_tbl):
        return BizDB.Interaction([models.Switch.DynUpdate(switch_tbl)])

    @classmethod
    def Remove(cls, rowids):
        return BizDB.Interaction(models.Switch.SqlRows_Remove(rowids))

    @classmethod
    async def Query(cls, sql_row):
        return await BizDB.Query(sql_row)

    @classmethod
    async def Get(cls, sql_row):
        rows = await cls.Query(sql_row)
        return rows[0] if rows else None

    @classmethod
    def UpdateName(cls, switchid, name, tag):
        sql_str = """update rgw_switch set name=?, tag=? where id=?"""
        sql_args = [name, tag, switchid]
        return BizDB.Interaction([[sql_str, sql_args]])

    @classmethod
    def UpdateUts(cls, switchids, uts):
        if not isinstance(switchids, list):
            switchids = [switchids]
        sql_rows = [["update rgw_switch set uts=? where id=?", [uts, sid]] for sid in switchids]
        return BizDB.Interaction(sql_rows)

    @classmethod
    def Search(cls, para):
        """
        :param para: {"name", "val"}
        :return: [cfg,...]
        """
        if para['name'] == "name":
            sql_str = """select r1.*
                          from rgw_switch r1 where r1.name like ? limit ?"""
        else:
            raise rg_lib.RGError(models.ErrorTypes.UnsupportedOp())
        sql_args = ("{0}%".format(para['val']), rgw_consts.DbConsts.SEARCH_LIMIT)
        return BizDB.Query([sql_str, sql_args])


class SysCfg:
    @classmethod
    def Set(cls, mdl):
        return BizDB.Interaction(models.SysCfg.DynUpsert(models.SysCfg.Filter(mdl)))

    @classmethod
    def Remove(cls, keys):
        return BizDB.Interaction(models.SysCfg.SqlRows_Remove(keys))

    @classmethod
    async def Get(cls, sql_row):
        rows = await BizDB.Query(sql_row)
        return {r['key']: r['val'] for r in rows}

    @classmethod
    async def GetTimezone(cls):
        """
        :return: pytz.timezone
        """
        import pytz
        tbl = await cls.Get(['select * from rgw_sys_cfg where key=?', ('timezone',)])
        if len(tbl) > 0:
            if len(tbl['timezone']) > 0:
                return pytz.timezone(tbl['timezone'])
            else:
                return pytz.timezone('UTC')
        else:
            return pytz.timezone('UTC')

    @classmethod
    async def GetDomain(cls):
        """
        :return: string
        """
        tbl = await cls.Get(['select * from rgw_sys_cfg where key=?', ('domain',)])
        domain = tbl['domain'] if len(tbl) > 0 else u''
        return domain

    @classmethod
    async def CheckPageKiteInfo(cls):
        """
        :return: addr id
        """
        tbl = await cls.Get(['select * from rgw_sys_cfg where key in (?,?,?,?)',
                             ('pagekite_path', 'pagekite_frontend', 'domain', 'pagekite_pwd')])
        if len(tbl) < 4:
            return None
        else:
            return None if '' in tbl.values() else tbl

    @classmethod
    async def CheckPwd(cls, pwd):
        tbl = await cls.Get(["select * from rgw_sys_cfg where key=? and val=?", ("pwd", pwd)])
        return len(tbl) > 0

    @classmethod
    async def GetGwInfo(cls):
        tbl = await cls.Get(['select * from rgw_sys_cfg where key = ?',
                             ('gw_url',)])
        if len(tbl) == 1 and len(tbl['gw_url']) > 0:
            return tbl
        else:
            return None

    @classmethod
    async def GetGwApiUrl(cls, rpc_no):
        tbl = await cls.GetGwInfo()
        if tbl:
            url = "{0}/{1}".format(tbl['gw_url'], rpc_no)
            return url
        else:
            return ''

    @classmethod
    async def GetElasticEmailInfo(cls):
        tbl = await cls.Get(['select * from rgw_sys_cfg where key in (?,?,?)',
                             ('elasticemail_api_key', 'elasticemail_send_url', 'email_sender')])
        if len(tbl) == 3 and len(tbl['elasticemail_api_key']) > 0 \
                and len(tbl['elasticemail_send_url']) > 0 and len(tbl['email_sender']) > 0:
            return {'api_key': tbl['elasticemail_api_key'],
                    'url': tbl['elasticemail_send_url'],
                    'sender': tbl['email_sender']}
        else:
            return None


class ElasticEmail:
    @classmethod
    async def SendEmail(cls, url, api_key, sender_email, to_emails, subject, content, timeout, retry=3):
        tbl = {'apikey': api_key,
               'from': sender_email,
               'msgTo': ",".join(to_emails),
               'bodyText': content + "\r\n",
               'isTransactional': True,
               'subject': subject}
        for i in range(retry):
            try:
                resp_defer = await treq.post(url, data=tbl, timeout=timeout)
                content = await resp_defer.json()
                return content
            except error.TimeoutError:
                pass
            except defer.CancelledError:
                pass
            await rg_lib.Twisted.sleep(1)
        else:
            raise error.TimeoutError()


class PageKite:
    manager = rg_lib.PageKiteManager()

    @classmethod
    async def RestartBackend(cls, http_port):
        cls.manager.Stop()
        tbl = await SysCfg.CheckPageKiteInfo()
        if tbl:
            cls.manager.SetPageKitePath(tbl['pagekite_path'])
            services = [
                'http:{0}:{1}:{2}:{3}'.format(tbl['domain'], 'localhost', http_port,
                                              tbl['pagekite_pwd']),
                'raw:{0}:{1}:{2}:{3}'.format(tbl['domain'], 'localhost', 22, tbl['pagekite_pwd'])
            ]
            cls.manager.StartBackend(tbl['pagekite_frontend'], services)


class SensorTrigger:
    mem_db = rg_lib.Sqlite.MakeMemoryConn()

    @classmethod
    async def Remove(cls, rowids):
        sql_rows = []
        for rowid in rowids:
            sql_rows.append([
                "delete from rgw_sensor_trigger where id=?",
                (rowid,)
            ])
            sql_rows.append([
                "delete from rgw_sensor_trigger_sensor where triggerid=?",
                (rowid,)
            ])
            sql_rows.append([
                "delete from rgw_sensor_trigger_switch where triggerid=?",
                (rowid,)
            ])
            await cls.RemoveCheckInterval(rowid)
        await BizDB.Interaction(sql_rows)

    @classmethod
    async def Query(cls, sql_row):
        """
        :param sql_row: [sql, args]
        :return: models.ConditionalRelaySwitchAction objs
        """
        rows = await BizDB.Query(sql_row)
        return [models.SensorTrigger.FromRow(r) for r in rows]

    @classmethod
    def SetCheckInterval(cls, mdl):
        key = rgw_consts.Keys.SENSOR_TRIGGER_INTERVAL.format(mdl['id'])
        return BizDB.redis_conn.set(key, 0, expire=mdl['check_interval'] * 60)

    @classmethod
    def RemoveCheckInterval(cls, rowid):
        return BizDB.redis_conn.delete(rgw_consts.Keys.SENSOR_TRIGGER_INTERVAL.format(rowid))

    @classmethod
    async def InCheckInterval(cls, rowid):
        return await BizDB.redis_conn.exists(rgw_consts.Keys.SENSOR_TRIGGER_INTERVAL.format(rowid)) > 0

    @classmethod
    def __Add(cls, conn_obj, mdl):
        cursor_obj = conn_obj.cursor()
        cursor_obj.execute("BEGIN")
        mdl1 = {k: mdl[k] for k in mdl if k not in ('switches', 'sensors')}
        sql_row = models.SensorTrigger.DynInsert(models.SensorTrigger.BeforeAdd(mdl1))
        cursor_obj.execute(sql_row[0], sql_row[1])
        cursor_obj.execute("select last_insert_rowid() newid")
        row = cursor_obj.fetchone()
        newid = row[0]
        for sensor in mdl['sensors']:
            cursor_obj.execute("""insert into rgw_sensor_trigger_sensor values(?,?,?,?)""",
                               (newid, sensor['sensorid'], sensor['op'], sensor['rval']))
        for device in mdl['switches']:
            cursor_obj.execute("""insert into rgw_sensor_trigger_switch values(?,?,?,?)""",
                               (newid, device['switchid'], device['action_no'], device['working_seconds']))
        cursor_obj.close()
        return newid

    @classmethod
    def __Update(cls, conn_obj, mdl):
        cursor_obj = conn_obj.cursor()
        cursor_obj.execute("BEGIN")
        mdl1 = {k: mdl[k] for k in mdl if k not in ('switches', 'sensors')}
        sql_row = models.SensorTrigger.DynUpdate(models.SensorTrigger.BeforeSet(mdl1))
        cursor_obj.execute(sql_row[0], sql_row[1])
        cursor_obj.execute("""delete from rgw_sensor_trigger_sensor where triggerid=?""",
                           (mdl['id'],))
        cursor_obj.execute("""delete from rgw_sensor_trigger_switch where triggerid=?""",
                           (mdl['id'],))
        for sensor in mdl['sensors']:
            cursor_obj.execute("""insert into rgw_sensor_trigger_sensor values(?,?,?,?)""",
                               (mdl['id'], sensor['sensorid'], sensor['op'], sensor['rval']))
        for device in mdl['switches']:
            cursor_obj.execute("""insert into rgw_sensor_trigger_switch values(?,?,?,?)""",
                               (mdl['id'], device['switchid'], device['action_no'], device['working_seconds']))
        cursor_obj.close()
        return mdl['id']

    @classmethod
    def __Upsert(cls, conn_obj, mdl):
        if models.SensorTrigger.HasId(mdl):
            return cls.__Update(conn_obj, mdl)
        else:
            return cls.__Add(conn_obj, mdl)

    @classmethod
    async def Upsert(cls, mdl):
        rowid = await rg_lib.Sqlite.RunWithConn(BizDB.db_pool, cls.__Upsert, mdl)
        await cls.RemoveCheckInterval(rowid)
        return rowid

    @classmethod
    async def Get(cls, sql_row):
        rows = await cls.Query(sql_row)
        return rows[0] if rows else None

    @classmethod
    async def GetMdl(cls, triggerid):
        row = await cls.Get(['select * from rgw_sensor_trigger where id=?', (triggerid,)])
        if row:
            row['switches'] = await cls.Query(["""select r1.switchid, r1.action_no, r1.working_seconds, r2.name switch_name 
                                              from rgw_sensor_trigger_switch r1, rgw_switch r2 
                                              where r1.switchid=r2.id and r1.triggerid=?""",
                                               (triggerid,)])
            row['sensors'] = await cls.Query(["""select r1.sensorid, r1.op, r1.rval, r2.name sensor_name 
                                              from rgw_sensor_trigger_sensor r1, rgw_sensor r2 
                                              where r1.sensorid=r2.id and r1.triggerid=?""",
                                              (triggerid,)])
            return row
        else:
            return None

    @classmethod
    def Eval(cls, expr, args):
        iter_obj = cls.mem_db.execute("select {0}".format(expr), tuple(args))
        for i in iter_obj:
            return i[0]


class TriggerLog:
    @classmethod
    def Add(cls, trigger_log):
        """
        :param trigger_log: models.TriggerLog or list of models.TriggerLog
        :return:
        """
        sql_rows = []
        if isinstance(trigger_log, list):
            for mdl in trigger_log:
                sql_rows.append(models.TriggerLog.DynInsert(mdl, True))
        else:
            sql_rows.append(models.TriggerLog.DynInsert(trigger_log, True))
        return LogDB.Interaction(sql_rows)

    @classmethod
    def GetLatest(cls, count):
        sql_str = "select * from rgw_trigger_log order by cts desc limit ?"
        sql_args = [count]
        return LogDB.Query([sql_str, sql_args])

    @classmethod
    def RemoveTTL(cls, ts_val):
        return LogDB.Interaction([
            ["delete from rgw_trigger_log where cts < ?", (ts_val,)]
        ])




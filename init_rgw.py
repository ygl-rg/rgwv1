import sqlite3
import rg_lib
import settings
import models


def SetPassword(connid):
    new_pwd = "root"
    connid.execute("insert into rgw_sys_cfg(key,val) values(?,?)", ("pwd", new_pwd))
    return new_pwd


def SetPagekite(connid):
    pk_path = "/home/pi/pagekite.py"
    connid.execute("insert into rgw_sys_cfg(key,val) values(?,?)", ("pagekite_path", pk_path))
    connid.execute("insert into rgw_sys_cfg(key,val) values(?,?)", ("pagekite_frontend", "esis.vip:80"))


def SetEmailSender(connid):
    sender = "service@roundgis.com"
    connid.execute("insert into rgw_sys_cfg(key,val) values(?,?)", ("email_sender", sender))


def SetRXG(connid):
    connid.execute("insert into rgw_sys_cfg(key,val) values(?,?)", ("gw_url", "http://localhost:8000"))


def main():
    with rg_lib.DbConnWrap(sqlite3.connect(settings.BIZ_DB['path'], check_same_thread=False)) as conn:
        conn.conn_obj.execute("PRAGMA journal_mode=WAL")
        conn.conn_obj.execute("PRAGMA synchronous=1")
    with rg_lib.DbConnWrap(sqlite3.connect(settings.BIZ_DB['path'], check_same_thread=False)) as conn:
        conn.conn_obj.execute("drop table if exists rgw_sys_cfg")
        conn.conn_obj.execute(rg_lib.Sqlite.CreateTable(models.SysCfg.TBL, models.SysCfg.TBL_FIELDS))
        SetPagekite(conn.conn_obj)
        SetEmailSender(conn.conn_obj)
        SetRXG(conn.conn_obj)
        new_pwd = SetPassword(conn.conn_obj)
        print('password is {0}'.format(new_pwd))


if __name__ == "__main__":
    main()



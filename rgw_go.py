import os.path as os_path
import sys
from twisted.internet import reactor, defer
from twisted.python import log, logfile
import rgw_consts
import web_app
import g_vars
import api_core
import api_switch_stats
from bkg_tasks import beat_tasks


def InitWebService():
    reactor.listenTCP(g_vars.g_cfg['http_port'], web_app.App(g_vars.g_cfg['web']['static_path'],
                                                             g_vars.g_cfg['web']['export_path']))


def UpdateConsts():
    for k in rgw_consts.Node_URLs.__dict__:
        if k.find('__') < 0:
            if k not in ('EXPORT_FMT', ):
                setattr(rgw_consts.Node_URLs, k,
                        os_path.join(g_vars.g_cfg['app_url_prefix'], rgw_consts.Node_URLs.__dict__[k]))

    for k in rgw_consts.Keys.__dict__:
        if k.find('__') < 0:
            temp = os_path.join(g_vars.g_cfg['app_url_prefix'], rgw_consts.Keys.__dict__[k])
            setattr(rgw_consts.Keys, k, temp.replace('/', '_'))

    for k in rgw_consts.Cookies.__dict__:
        if k.find('__') < 0:
            temp = os_path.join(g_vars.g_cfg['app_url_prefix'], rgw_consts.Cookies.__dict__[k])
            setattr(rgw_consts.Keys, k, temp.replace('/', '_'))


async def Init(cfg):
    await api_core.BizDB.Init(cfg)
    await api_core.LogDB.Init(cfg)
    api_switch_stats.Init()
    await api_core.PageKite.RestartBackend(cfg['http_port'])
    InitWebService()
    await beat_tasks.Setup()


def main(cfg_file):
    try:
        g_vars.LoadConfig(cfg_file)
        UpdateConsts()
        log.startLogging(logfile.DailyLogFile.fromFullPath(g_vars.g_cfg['path']["syslog"] + "/" +
                                                           "rgw"+"".join([i for i in g_vars.g_cfg['host'] if i != '.']) + "_log.txt"),
                         setStdout=False)
        reactor.callLater(1, defer.ensureDeferred, Init(g_vars.g_cfg))
        reactor.addSystemEventTrigger('before', 'shutdown', api_core.BizDB.Close)
        reactor.addSystemEventTrigger('before', 'shutdown', api_core.LogDB.Close)
        reactor.addSystemEventTrigger('before', 'shutdown', beat_tasks.Close)
        reactor.run()
    except Exception:
        log.err()


if __name__ == "__main__":
    args = sys.argv
    main(args[1])


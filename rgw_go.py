import os.path as os_path
from twisted.internet import reactor, defer
from twisted.python import log, logfile
import settings
import rgw_consts
import web_app
import api_core
import api_switch_stats
from bkg_tasks import beat_tasks


def InitWebService():
    reactor.listenTCP(settings.HTTP_PORT, web_app.App(settings.WEB['static_path'], settings.WEB['export_path']))


def UpdateConsts():
    for k in rgw_consts.URLs.__dict__:
        if k.find('__') < 0:
            if k not in ('EXPORT_FMT', ):
                setattr(rgw_consts.URLs, k,
                        os_path.join(settings.URL_PREFIX, rgw_consts.URLs.__dict__[k]))

    for k in rgw_consts.Keys.__dict__:
        if k.find('__') < 0:
            temp = os_path.join(settings.URL_PREFIX, rgw_consts.Keys.__dict__[k])
            setattr(rgw_consts.Keys, k, temp.replace('/', '_'))

    for k in rgw_consts.Cookies.__dict__:
        if k.find('__') < 0:
            temp = os_path.join(settings.URL_PREFIX, rgw_consts.Cookies.__dict__[k])
            setattr(rgw_consts.Keys, k, temp.replace('/', '_'))


async def Init():
    await api_core.BizDB.Init()
    await api_core.LogDB.Init()
    api_switch_stats.Init()
    await api_core.PageKite.RestartBackend(settings.HTTP_PORT)
    InitWebService()
    await beat_tasks.Setup()


def main():
    try:
        UpdateConsts()
        log.startLogging(logfile.DailyLogFile.fromFullPath(settings.LOG_PATH + "/" +
                                                           "rgw"+"".join([i for i in settings.HOST if i != '.']) + "_log.txt"),
                         setStdout=False)
        reactor.callLater(1, defer.ensureDeferred, Init())
        reactor.addSystemEventTrigger('before', 'shutdown', api_core.BizDB.Close)
        reactor.addSystemEventTrigger('before', 'shutdown', api_core.LogDB.Close)
        reactor.addSystemEventTrigger('before', 'shutdown', beat_tasks.Close)
        reactor.run()
    except Exception:
        log.err()


if __name__ == "__main__":
    main()


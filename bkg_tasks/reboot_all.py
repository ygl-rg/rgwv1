from twisted.python import log
import api_rxg


async def Run():
    try:
        await api_rxg.ZbModule.RebootAll()
    except Exception as e:
        log.err()

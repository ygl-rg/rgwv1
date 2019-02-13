from twisted.python import log
import api_rxg


async def Run():
    try:
        await api_rxg.RebootAll()
    except Exception as e:
        log.err()

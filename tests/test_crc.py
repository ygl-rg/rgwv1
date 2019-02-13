from __future__ import absolute_import
import pytest
import rgy_a7.a7_core.rg_cores.util as rg_util


@pytest.mark.skipif(False, reason='')
class TestCRC(object):
    @pytest.mark.skipif(False, reason='')
    def test_crc16(self):
        test = '\x01\x03\x00\x8D\x00\x05'
        res = rg_util.Bytes.crc16(test)
        assert ((res & 0xFF) == 21) and ((res >> 8) & 0xFF) == 226

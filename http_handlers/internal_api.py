import functools
import rg_lib
from . import em_api
from . import sys_cfg_api
from http_handlers import sensor_api, switch_api, \
    sensor_trigger_api as cond_api
from . import zb_module_api
from . import zb_device_api


class Base(rg_lib.AsyncDynFuncHandler):
    def initialize(self, **kwargs):
        self.FUNC_TBL = {}

    def GetFunc(self, func_name):
        return self.FUNC_TBL[func_name] if func_name in self.FUNC_TBL else None


class EnvMonitor(Base):
    def initialize(self, **kwargs):
        self.FUNC_TBL = {"OpenSwitch": functools.partial(em_api.OpenSwitch, self),
                         "CloseSwitch": functools.partial(em_api.CloseSwitch, self),
                         'GetSwitch': functools.partial(em_api.GetSwitch, self),
                         'AddSchedule': functools.partial(em_api.AddSchedule, self),
                         'ListSchedule': functools.partial(em_api.ListSchedule, self),
                         'RemoveSchedule': functools.partial(em_api.RemoveSchedule, self),
                         'GetSensor': functools.partial(em_api.GetSensor, self),
                         'FindSensorMinsAvgLog': functools.partial(em_api.FindSensorMinsAvgLog, self),
                         'ExportSensorMinsAvgLog': functools.partial(em_api.ExportSensorMinsAvgLog, self),
                         'GetSwitchOnDetail': functools.partial(em_api.GetSwitchOnDetail, self),
                         'GetLatestTriggerLog': functools.partial(em_api.GetLatestTriggerLog, self),
                         'UpdateDeviceName': functools.partial(em_api.UpdateDeviceName, self),
                         'ListSwitchMonthlyUsage': functools.partial(em_api.ListSwitchMonthlyUsage, self),
                         'ExportSwitchMonthlyUsage': functools.partial(em_api.ExportSwitchMonthlyUsage, self)}


class SysCfg(Base):
    def initialize(self, **kwargs):
        self.FUNC_TBL = {"SetCfg": functools.partial(sys_cfg_api.SetCfg, self),
                         "GetCfg": functools.partial(sys_cfg_api.GetCfg, self),
                         "RebootSys": functools.partial(sys_cfg_api.RebootSys, self),
                         "RestartSys": functools.partial(sys_cfg_api.RestartSys, self),
                         'RegisterDevice': functools.partial(sys_cfg_api.RegisterDevice, self),
                         'SyncDevice': functools.partial(sys_cfg_api.SyncDevice, self)}


class SensorAdm(Base):
    def initialize(self, **kwargs):
        self.FUNC_TBL = {"AddSensor": functools.partial(sensor_api.AddSensor, self),
                         "SetSensor": functools.partial(sensor_api.SetSensor, self),
                         "GetSensor": functools.partial(sensor_api.GetSensor, self),
                         'RemoveSensor': functools.partial(sensor_api.RemoveSensor, self),
                         'SearchSensor': functools.partial(sensor_api.SearchSensor, self),
                         'SyncSensor': functools.partial(sensor_api.SyncSensor, self)}


class SensorTriggerAdm(Base):
    def initialize(self, **kwargs):
        self.FUNC_TBL = {"FindTrigger": functools.partial(cond_api.FindTrigger, self),
                         'RemoveTrigger': functools.partial(cond_api.RemoveTrigger, self),
                         'SetTrigger': functools.partial(cond_api.SetTrigger, self),
                         'GetTrigger': functools.partial(cond_api.GetTrigger, self)
                         }


class SwitchAdm(Base):
    def initialize(self, **kwargs):
        self.FUNC_TBL = {"AddSwitch": functools.partial(switch_api.AddSwitch, self),
                         "SetSwitch": functools.partial(switch_api.SetSwitch, self),
                         "GetSwitch": functools.partial(switch_api.GetSwitch, self),
                         'RemoveSwitch': functools.partial(switch_api.RemoveSwitch, self),
                         'SearchSwitch': functools.partial(switch_api.SearchSwitch, self),
                         'SyncSwitch': functools.partial(switch_api.SyncSwitch, self)}


class ZbModuleAdm(Base):
    def initialize(self, **kwargs):
        self.FUNC_TBL = {"ListModule": functools.partial(zb_module_api.ListModule, self),
                         'ProbeDevice': functools.partial(zb_module_api.ProbeDevice, self),
                         'ResetModule': functools.partial(zb_module_api.ResetModule, self),
                         'BackupModule': functools.partial(zb_module_api.BackupModule, self),
                         'RestoreModule': functools.partial(zb_module_api.RestoreModule, self),
                         'RebootModule': functools.partial(zb_module_api.RebootModule, self),
                         'RebootAll': functools.partial(zb_module_api.RebootAll, self)}


class ZbDeviceAdm(Base):
    def initialize(self, **kwargs):
        self.FUNC_TBL = {"AddDevice": functools.partial(zb_device_api.Add, self),
                         "SetDevice": functools.partial(zb_device_api.Set, self),
                         "GetDevice": functools.partial(zb_device_api.Get, self),
                         "GetDeviceNId": functools.partial(zb_device_api.GetNId, self),
                         'RemoveDevice': functools.partial(zb_device_api.Remove, self),
                         'ResetDevice': functools.partial(zb_device_api.Reset, self),
                         'SearchDevice': functools.partial(zb_device_api.Search, self),
                         'GetDeviceOpLog': functools.partial(zb_device_api.GetOpLog, self),
                         'GetDeviceOpErrorCount': functools.partial(zb_device_api.GetOpErrorCount, self),
                         'RebootDevice': functools.partial(zb_device_api.Reboot, self)
                         }

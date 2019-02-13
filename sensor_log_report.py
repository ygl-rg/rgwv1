import xlsxwriter
import rg_lib


def Make(file_obj, data_log_tbl):
    """
    :param file_obj: str or IO Obj
    :param data_log_tbl: {"sensorids":[], "log_tbl": {sensorid->{cts: data,}, ...},
                          "sensors_tbl": {sensorid->sensor tbl},
                          "ts_series": [series of timestamp],
                          'tz_offset': timezone offset optional}
    :return: None
    """
    wb = None
    try:
        wb = xlsxwriter.Workbook(file_obj)
        bold_format = wb.add_format()
        bold_format.set_bold()
        bold_format.set_align('center')
        dt_fmt_obj = wb.add_format()
        dt_fmt_obj.set_num_format("yyyy-mm-dd hh:mm")
        dt_fmt_obj.set_align('center')
        tz_offset = data_log_tbl.get('tz_offset', 0)
        ws = wb.add_worksheet('Log')
        ws.write_string(0, 0, "Time", bold_format)
        ws.set_column(0, 0, 22)
        for idx, sensorid in enumerate(data_log_tbl['sensorids']):
            sid_str = str(sensorid)
            ws.write_string(0, idx+1, data_log_tbl['sensors_tbl'][sid_str]['name'], bold_format)
        row, col = 1, 0
        for i, ts in enumerate(data_log_tbl['ts_series']):
            ws.write_number(row, 0, rg_lib.DateTime.ts2excel(ts + tz_offset), dt_fmt_obj)
            for j, sensorid in enumerate(data_log_tbl['sensorids']):
                sid_str = str(sensorid)
                temp = data_log_tbl['log_tbl'][sid_str]
                if ts in temp:
                    ws.write_string(row, j+1, "{0:0.2f}{1}".format(temp[ts]['avg_val'],
                                                                   data_log_tbl['sensors_tbl'][sid_str].get("val_unit", u"")))
                else:
                    ws.write_string(row, j+1, '')
            row += 1
    finally:
        if wb:
            wb.close()

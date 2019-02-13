import xlsxwriter
import rg_lib


def Make(file_obj, arg):
    """
    :param file_obj: str or IO Obj
    :param arg: {"switches": [switch modls], "rec_tbl": {switchid:[SwitchOpDuration,...]},
                 "year": year, "month": month}
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
        ws = wb.add_worksheet('Switch Usage')
        ws.write_string(0, 0, "Name", bold_format)
        ws.set_column(0, 0, 32)
        days = len(arg['rec_tbl'][arg['switches'][0]['id']])
        for i in range(days):
            ws.write_string(0, i+1, "{0:04}-{1:02}-{2:02}".format(arg['year'], arg['month'], i+1),
                            bold_format)
            ws.set_column(0, i+1, 16)
        for idx, i in enumerate(arg['switches']):
            ws.write_string(idx+1, 0, i['name'], bold_format)
            for idx1, j in enumerate(arg['rec_tbl'][i['id']]):
                ws.write_string(idx+1, idx1+1, rg_lib.DateTime.seconds2hhmmss(j['val']))
    finally:
        if wb:
            wb.close()

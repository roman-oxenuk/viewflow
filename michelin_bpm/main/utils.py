# -*- coding: utf-8 -*-
import xlrd
from xlutils.filter import process, XLRDReader, XLWTWriter


def render_excel_template(template_path, context, filename):
    """Заполняет excel-шаблон данными из контекста и сохраняет результат в файл."""
    def copy2(wb):
        w = XLWTWriter()
        process(XLRDReader(wb, 'unknown.xls'), w)
        return w.output[0][1], w.style_list

    rdbook = xlrd.open_workbook(template_path, formatting_info=True)
    sheet_name = 'Main list'
    rdsheet = rdbook.sheet_by_name(sheet_name)
    wtbook, style_list = copy2(rdbook)
    wtsheet = wtbook.get_sheet(sheet_name)
    for pos, value in context.items():
        rowx, colx = pos
        xf_index = rdsheet.cell_xf_index(rowx, colx)
        if not value:
            value = ''
        wtsheet.write(rowx, colx, str(value), style_list[xf_index])
    wtbook.save(filename)

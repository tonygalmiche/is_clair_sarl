# -*- coding: utf-8 -*-
from copy import copy
from importlib.resources import path
from odoo import models,fields,api
from odoo.http import request
from odoo.exceptions import Warning
import datetime
import base64
import os
import openpyxl
import logging
_logger = logging.getLogger(__name__)


class sale_order(models.Model):
    _inherit = "sale.order"

    is_import_excel_ids = fields.Many2many('ir.attachment', 'sale_order_is_import_excel_ids_rel', 'order_id', 'attachment_id', 'Import xlsx')



    def import_fichier_xlsx(self):
        for obj in self:
            print(obj)




            obj.order_line.unlink()
            for attachment in obj.is_import_excel_ids:
                xlsxfile=base64.b64decode(attachment.datas)

                path = '/tmp/sale_order-'+str(obj.id)+'.xlsx'
                f = open(path,'wb')
                f.write(xlsxfile)
                f.close()
                #*******************************************************************

                #** Test si fichier est bien du xlsx *******************************
                try:
                    #wb = openpyxl.load_workbook(filename = path)
                    wb    = openpyxl.load_workbook(filename = path, data_only=True)
                    ws    = wb.active
                    cells = list(ws)
                except:
                    raise Warning(u"Le fichier "+attachment.name+u" n'est pas un fichier xlsx")
                #*******************************************************************

                lig=0
                for row in ws.rows:
                    name = cells[lig][0].value
                    if name:
                        print(name)
                        try:
                            qty = float(cells[lig][2].value or 0)
                        except ValueError:
                            qty = 0
                        try:
                            price = float(cells[lig][4].value or 0)
                        except ValueError:
                            price = 0
                        if price>0 and qty>0:
                            vals={
                                "order_id": obj.id,
                                "product_id": 1,
                                "sequence"    : lig,
                                "name"        : name,
                                "product_uom_qty": qty,
                                "price_unit"     : price,
                            }
                            res = self.env['sale.order.line'].create(vals)
                    lig+=1



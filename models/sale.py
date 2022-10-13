# -*- coding: utf-8 -*-
#from copy import copy
#from importlib.resources import path
#from itertools import product
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

    is_import_excel_ids     = fields.Many2many('ir.attachment' , 'sale_order_is_import_excel_ids_rel', 'order_id'     , 'attachment_id'    , 'Devis .xlsx à importer')
    is_taches_associees_ids = fields.One2many('purchase.order', 'is_sale_order_id', 'Tâches associées')
    is_affaire_id           = fields.Many2one('is.affaire', 'Affaire')


    def import_fichier_xlsx(self):
        for obj in self:
            obj.order_line.unlink()
            sequence=0
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
                    ref  = cells[lig][7].value

                    vals=False
                    if ref=="SECTION":
                        vals={
                            "order_id"       : obj.id,
                            "sequence"       : sequence,
                            "name"           : name,
                            "product_uom_qty": 0,
                            "display_type"   : "line_section",
                        }
                        filtre=[
                            ("is_sale_order_id"  ,"=", obj.id),
                            ("partner_ref"  ,"=", name),
                        ]
                        orders = self.env['purchase.order'].search(filtre)
                        if orders:
                            purchase_order = orders[0]
                            purchase_order.order_line.unlink()
                        else:
                            v={
                                "partner_id"      : 1,
                                "is_sale_order_id": obj.id,
                                "partner_ref"     : name,
                                "is_affaire_id"   : obj.is_affaire_id.id,
                            }
                            purchase_order = self.env['purchase.order'].create(v)

                    if ref=="NOTE":
                        vals={
                            "order_id"       : obj.id,
                            "sequence"       : sequence,
                            "name"           : name,
                            "product_uom_qty": 0,
                            "display_type"   : "line_note",
                        }



                    if name and ref and not vals:
                        filtre=[
                            ("default_code"  ,"=", ref),
                        ]
                        products = self.env['product.product'].search(filtre)
                        if products:
                            product=products[0]
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
                                    "product_id": product.id,
                                    "sequence"    : sequence,
                                    "name"        : name,
                                    "product_uom_qty": qty,
                                    "price_unit"     : price,
                                }
                                if purchase_order:
                                    v={
                                        "order_id"    : purchase_order.id,
                                        "product_id"  : product.id,
                                        "sequence"    : sequence,
                                        "name"        : name,
                                        "product_qty" : qty,
                                    }
                                    if product.is_sous_article_ids:
                                        for line in product.is_sous_article_ids:
                                            v["product_id"]=line.product_id.id
                                            res = self.env['purchase.order.line'].create(v)
                                    else:
                                        res = self.env['purchase.order.line'].create(v)


                    if vals:
                        res = self.env['sale.order.line'].create(vals)
                    lig+=1
                    sequence+=1



# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.http import request
from odoo.exceptions import Warning
import datetime
import base64
import os
import openpyxl
import logging
_logger = logging.getLogger(__name__)


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    order_id      = fields.Many2one('sale.order', string='Order Reference', required=False, ondelete='cascade', index=True, copy=False)
    is_section_id = fields.Many2one('is.sale.order.section', 'Section', index=True)


class is_sale_order_section(models.Model):
    _name='is.sale.order.section'
    _description = "Sections des commandes"
    _rec_name = 'section'
    _order='sequence'

    order_id = fields.Many2one('sale.order', 'Commande', required=True, ondelete='cascade')
    sequence = fields.Integer("Sequence")
    section  = fields.Char("Section", required=True)
    option   = fields.Boolean("Option", default=False)
    line_ids = fields.One2many('sale.order.line', 'is_section_id', 'Lignes')



    def option_section_action(self):
        for obj in self:
            obj.option = not obj.option
            for line in obj.line_ids:
                print(line,obj.option,obj.order_id.id)
                if obj.option:
                    line.order_id=False
                else:
                    line.order_id=obj.order_id.id


                print(line.order_id)


    def lignes_section_action(self):
        for obj in self:
            return {
                "name": "Section "+str(obj.section),
                "view_mode": "tree,form",
                "res_model": "sale.order.line",
                "domain": [
                    ("is_section_id","=",obj.id),
                ],
                "type": "ir.actions.act_window",
            }


class sale_order(models.Model):
    _inherit = "sale.order"

    is_import_excel_ids     = fields.Many2many('ir.attachment' , 'sale_order_is_import_excel_ids_rel', 'order_id'     , 'attachment_id'    , 'Devis .xlsx à importer')
    is_import_alerte        = fields.Text('Alertes importation')
    is_taches_associees_ids = fields.One2many('purchase.order', 'is_sale_order_id', 'Tâches associées')
    is_affaire_id           = fields.Many2one('is.affaire', 'Affaire')
    is_section_ids          = fields.One2many('is.sale.order.section', 'order_id', 'Sections')


    def import_fichier_xlsx(self):
        for obj in self:
            obj.order_line.unlink()
            obj.is_section_ids.unlink()
            sequence=0
            alertes=[]
            section_id=False
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
                option=False
                for row in ws.rows:
                    name = cells[lig][0].value
                    ref  = cells[lig][7].value

                    print(ref,section_id)



                    vals=False
                    if ref in ["SECTION", "OPTION"] and name:
                        vals={
                            "order_id"       : obj.id,
                            "sequence"       : sequence,
                            "section"        : name,
                        }
                        option=False
                        if ref=="OPTION":
                            vals["option"]=True
                            option=True
                        section = self.env['is.sale.order.section'].create(vals)
                        section_id=section.id

                        vals={
                            "order_id"       : not option and obj.id,
                            "sequence"       : sequence,
                            "name"           : name,
                            "product_uom_qty": 0,
                            "display_type"   : "line_section",
                            "is_section_id"  : section_id,
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

                    if ref=="NOTE" and name:
                        vals={
                            "order_id"       : not option and obj.id,
                            "sequence"       : sequence,
                            "name"           : name,
                            "product_uom_qty": 0,
                            "display_type"   : "line_note",
                            "is_section_id"  : section_id,
                        }



                    if name and ref and not vals:
                        filtre=[
                            ("default_code"  ,"=", ref),
                        ]
                        products = self.env['product.product'].search(filtre)
                        if not products:
                            alertes.append("Code '%s' non trouvé"%(ref))
                        else:
                            product=products[0]
                            try:
                                qty = float(cells[lig][2].value or 0)
                            except ValueError:
                                qty = 0
                            try:
                                price = float(cells[lig][4].value or 0)
                            except ValueError:
                                price = 0
                            vals={
                                "order_id": not option and obj.id,
                                "product_id": product.id,
                                "sequence"    : sequence,
                                "name"        : name,
                                "product_uom_qty": qty,
                                "price_unit"     : price,
                                "product_uom" : product.uom_id.id,
                                "is_section_id"  : section_id,
                            }
                            if purchase_order:
                                v={
                                    "order_id"    : purchase_order.id,
                                    "product_id"  : product.id,
                                    "sequence"    : sequence,
                                    "name"        : name,
                                    "product_qty" : qty,
                                    "display_type": False,
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

            if alertes:
                alertes = "\n".join(alertes)
            else:
                alertes=False

            obj.is_import_alerte = alertes




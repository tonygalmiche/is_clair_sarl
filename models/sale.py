# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
import datetime
import base64
import os
import openpyxl
import logging
_logger = logging.getLogger(__name__)


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    @api.depends('is_facturable_pourcent','price_unit','product_uom_qty')
    def _compute_facturable(self):
        cr,uid,context,su = self.env.args
        for obj in self:

            is_deja_facture=0
            if not isinstance(obj.id, models.NewId):
                SQL="""
                    SELECT sum(aml.is_a_facturer)
                    FROM account_move_line aml join account_move am on aml.move_id=am.id
                    WHERE aml.is_sale_line_id=%s and am.state!='cancel'
                """
                cr.execute(SQL,[obj.id])
                for row in cr.fetchall():
                    is_deja_facture = row[0] or 0
            is_facturable = obj.price_subtotal*obj.is_facturable_pourcent/100
            is_a_facturer = is_facturable - is_deja_facture
            obj.is_facturable   = is_facturable
            obj.is_deja_facture = is_deja_facture
            obj.is_a_facturer   = is_a_facturer


    order_id               = fields.Many2one('sale.order', string='Order Reference', required=False, ondelete='cascade', index=True, copy=False)
    is_section_id          = fields.Many2one('is.sale.order.section', 'Section', index=True)
    is_facturable_pourcent = fields.Float("% facturable", digits=(14,2), copy=False)
    is_facturable          = fields.Float("Facturable"  , digits=(14,2), store=False, readonly=True, compute='_compute_facturable')
    is_deja_facture        = fields.Float("Déja facturé", digits=(14,2), store=False, readonly=True, compute='_compute_facturable')
    is_a_facturer          = fields.Float("A Facturer"  , digits=(14,2), store=False, readonly=True, compute='_compute_facturable')
    is_prix_achat          = fields.Float("Prix d'achat", digits=(14,4))
    is_masquer_ligne       = fields.Boolean("Masquer",default=False,help="Masquer la ligne sur le PDF de la commande")


class is_sale_order_section(models.Model):
    _name='is.sale.order.section'
    _description = "Sections des commandes"
    _rec_name = 'section'
    _order='sequence'

    order_id   = fields.Many2one('sale.order', 'Commande', required=True, ondelete='cascade')
    sequence   = fields.Integer("Sequence")
    section    = fields.Char("Section", required=True)
    facturable_pourcent = fields.Float("% facturable", digits=(14,2))
    option     = fields.Boolean("Option", default=False)
    line_ids   = fields.One2many('sale.order.line', 'is_section_id', 'Lignes')


    def write(self, vals):
        res = super(is_sale_order_section, self).write(vals)
        if "facturable_pourcent" in vals:
            for obj in self:
                for line in obj.order_id.order_line:
                    if line.is_section_id==obj:
                        line.is_facturable_pourcent = vals["facturable_pourcent"]
        if "sequence" in vals:
            for obj in self:
                x=10
                for line in obj.order_id.order_line:
                    if line.is_section_id==obj:
                        line.sequence = vals["sequence"]*10000+x
                    x+=10
        return res


    def option_section_action(self):
        for obj in self:
            obj.option = not obj.option
            for line in obj.line_ids:
                if obj.option:
                    line.order_id=False
                else:
                    line.order_id=obj.order_id.id


    def lignes_section_action(self):
        for obj in self:
            tree_id = self.env.ref('is_clair_sarl.is_view_order_line_tree').id
            return {
                "name": "Section "+str(obj.section),
                "view_mode": "tree",
                "res_model": "sale.order.line",
                "domain": [
                    ("is_section_id","=",obj.id),
                    ("product_id","!=",False),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[tree_id, "tree"]],
            }


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.depends('order_line')
    def _compute_facturable(self):
        for obj in self:
            is_a_facturer=0
            for line in obj.order_line:
                is_a_facturer+=line.is_a_facturer
            obj.is_a_facturer=is_a_facturer

    is_import_excel_ids     = fields.Many2many('ir.attachment' , 'sale_order_is_import_excel_ids_rel', 'order_id'     , 'attachment_id'    , 'Devis .xlsx à importer')
    is_import_alerte        = fields.Text('Alertes importation')
    is_taches_associees_ids = fields.One2many('purchase.order', 'is_sale_order_id', 'Tâches associées')
    is_affaire_id           = fields.Many2one('is.affaire', 'Affaire')
    is_section_ids          = fields.One2many('is.sale.order.section', 'order_id', 'Sections')
    is_invoice_ids          = fields.One2many('account.move', 'is_order_id', 'Factures', readonly=True) #, domain=[('state','=','posted')])
    is_a_facturer           = fields.Float("A Facturer", digits=(14,2), store=False, readonly=True, compute='_compute_facturable')
    is_affichage_pdf        = fields.Selection([
        ('standard'       , 'Standard'),
        ('masquer_montant', 'Masquer le détail des montants'),
        ('total_section'  , 'Afficher uniquement le total des sections'),
    ], 'Affichage PDF', default='standard', required=True)

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
                    name    = cells[lig][0].value
                    ref     = cells[lig][7].value
                    is_masquer_ligne = False
                    try:
                        masquer = cells[lig][10].value # Colonne K => Mettre un x pour masquer la ligne sur le PDF
                        if masquer=="x":
                            is_masquer_ligne = True
                    except:
                        is_masquer_ligne = False
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
                        #TODO : Désactivation de la création des taches le 07/10/2023
                        # orders = self.env['purchase.order'].search(filtre)
                        # if orders:
                        #     purchase_order = orders[0]
                        #     purchase_order.order_line.unlink()
                        # else:
                        #     v={
                        #         "partner_id"      : 1,
                        #         "is_sale_order_id": obj.id,
                        #         "partner_ref"     : name,
                        #         "is_affaire_id"   : obj.is_affaire_id.id,
                        #     }
                        #     purchase_order = self.env['purchase.order'].create(v)

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
                        qty=price=discount=is_prix_achat=0
                        if not products:
                            alertes.append("Code '%s' non trouvé"%(ref))
                        else:
                            product=products[0]
                            try:
                                qty = float(cells[lig][2].value or 0)
                            except :
                                qty = 0
                            try:
                                price = float(cells[lig][4].value or 0)
                            except:
                                price = 0
                            try:
                                discount = float(cells[lig][8].value or 0)
                            except:
                                discount = 0
                            try:
                                is_prix_achat = float(cells[lig][9].value or 0)
                            except:
                                is_prix_achat = 0
                            vals={
                                "order_id"       : not option and obj.id,
                                "product_id"     : product.id,
                                "sequence"       : sequence,
                                "name"           : name,
                                "product_uom_qty": qty,
                                "price_unit"     : price,
                                "discount"       : discount,
                                "is_prix_achat"  : is_prix_achat,
                                "product_uom"    : product.uom_id.id,
                                "is_section_id"  : section_id,
                                "is_masquer_ligne": is_masquer_ligne,
                            }
                            #TODO : Désactivation de la création des taches le 07/10/2023
                            # if purchase_order:
                            #     v={
                            #         "order_id"    : purchase_order.id,
                            #         "product_id"  : product.id,
                            #         "sequence"    : sequence,
                            #         "name"        : name,
                            #         "product_qty" : qty,
                            #         "display_type": False,
                            #     }
                            #     if product.is_sous_article_ids:
                            #         for line in product.is_sous_article_ids:
                            #             v["product_id"]=line.product_id.id
                            #             res = self.env['purchase.order.line'].create(v)
                            #     else:
                            #         res = self.env['purchase.order.line'].create(v)
                    if vals:
                        res = self.env['sale.order.line'].create(vals)
                    lig+=1
                    sequence+=1
            if alertes:
                alertes = "\n".join(alertes)
            else:
                alertes=False
            obj.is_import_alerte = alertes


    def generer_facture_action(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            if obj.is_a_facturer==0:
                raise ValidationError("Il n'y a rien à facturer")
            products = self.env['product.product'].search([("default_code","=",'FACTURE')])
            if not len(products):
                raise ValidationError("Article 'FACTURE' non trouvé")
            product=products[0]

            #** Création des lignes *******************************************
            invoice_line_ids=[]
            sequence=0
            for line in obj.order_line:
                if line.display_type=="line_section":
                    vals={
                        'sequence'    : line.sequence,
                        'display_type': 'line_section',
                        'name'        : line.name,
                    }
                else:
                    #quantity=0
                    #if line.price_subtotal>0:
                    #    quantity=line.product_uom_qty*line.is_a_facturer/line.price_subtotal

                    quantity=line.product_uom_qty*line.is_facturable_pourcent/100

                    taxes = line.product_id.taxes_id
                    taxes = obj.fiscal_position_id.map_tax(taxes)
                    tax_ids=[]
                    for tax in taxes:
                        tax_ids.append(tax.id)
                    vals={
                        'sequence'  : line.sequence,
                        'product_id': line.product_id.id,
                        'name'      : line.name,
                        'quantity'  : quantity,
                        'is_facturable_pourcent': line.is_facturable_pourcent,
                        'price_unit'            : line.price_unit,
                        'is_sale_line_id'       : line.id,
                        'tax_ids'               : tax_ids,
                        "is_a_facturer"         : line.is_a_facturer,
                    }
                invoice_line_ids.append(vals)
                sequence=line.sequence

            #** Ajout des factures ********************************************
            invoices = self.env['account.move'].search([("is_order_id","=",obj.id)])
            for invoice in invoices:

                taxes = product.taxes_id
                taxes = obj.fiscal_position_id.map_tax(taxes)
                tax_ids=[]
                for tax in taxes:
                    tax_ids.append(tax.id)
                sequence+=10
                vals={
                    'sequence'  : sequence,
                    'product_id': product.id,
                    'name'      : invoice.name,
                    'quantity'  : -1,
                    'price_unit': invoice.amount_untaxed_signed,
                    'tax_ids'   : tax_ids,
                }
                invoice_line_ids.append(vals)


            #** Création entête facture ***************************************
            vals={
                'invoice_date'      : datetime.date.today(),
                'partner_id'        : obj.partner_id.id,
                'is_order_id'       : obj.id,
                'fiscal_position_id': obj.fiscal_position_id.id,
                'move_type'         : 'out_invoice',
                'invoice_line_ids'  : invoice_line_ids,
            }
            move=self.env['account.move'].create(vals)
            move.action_post()

    #         #** Ajout des factures réalisées ***********************************
    #         filtre=[
    #             ('is_contrat_id','=',obj.id),
    #             ('date_invoice','<=',datetime.date.today()),
    #             ('state','not in',['cancel']),
    #             ('id','!=',invoice_id),
    #         ]
    #         factures = self.env['account.invoice'].search(filtre,order='date_invoice')
    #         for facture in  factures:
    #             vals={
    #                 'invoice_id'   : invoice_id,
    #                 'product_id'   : 2,
    #                 'name'         : facture.number,
    #                 'quantity'     : 1,
    #                 #'price_unit'   : -facture.amount_untaxed,
    #                 'price_unit'   : 0,
    #                 'account_id'   : 622, #701100
    #                 'is_invoice_id': facture.id,
    #             }
    #             invoice_line=self.env['account.invoice.line'].create(vals)
    #             line_res = invoice_line.uptate_onchange_product_id()
    #             vals={
    #                 'name'      : facture.number,
    #                 #'price_unit': -facture.amount_untaxed,
    #                 'price_unit'   : -facture.is_montant_hors_revision,
    #             }
    #             invoice_line.write(vals)
    #         #*******************************************************************

    #         #** Recalcul de la TVA et validation de la facture *****************
    #         res_validate = invoice.update_tva_account_action()
    #         res_validate = invoice.compute_taxes()
    #         try:
    #             res_validate = invoice.action_invoice_open()
    #         except:
    #             continue
    #         #*******************************************************************

    #         obj.compute_restant_ht()

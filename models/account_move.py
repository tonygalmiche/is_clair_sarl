# -*- coding: utf-8 -*-
from odoo import models,fields,api


class AccountMove(models.Model):
    _inherit = "account.move"

    is_order_id         = fields.Many2one('sale.order', 'Commande')
    is_affaire_id       = fields.Many2one('is.affaire', 'Affaire', related='is_order_id.is_affaire_id')
    is_banque_id        = fields.Many2one('account.journal', 'Banque par défaut', related='partner_id.is_banque_id')
    is_export_compta_id = fields.Many2one('is.export.compta', 'Folio', copy=False)


    def acceder_facture_action(self):
        for obj in self:
            res= {
                'name': 'Facture',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': obj.id,
                'type': 'ir.actions.act_window',
                # 'view_id': self.env.ref('account.invoice_form').id,
                'domain': [('type','=','out_invoice')],
            }
            return res


    def action_post(self):
        res = super().action_post()
        print(res)

        for obj in self:
            vals={
                "partner_id": obj.partner_id.id,
                "affaire_id": obj.is_affaire_id.id,
                "invoice_id": obj.id,
                "objet"     : "Validation facture",
                "montant"   : obj.amount_untaxed_signed,
            }
            courrier = self.env['is.courrier.expedie'].create(vals)


        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_affaire_id   = fields.Many2one('is.affaire', 'Affaire')
    is_sale_line_id = fields.Many2one('sale.order.line', 'Ligne de commande', index=True)
    is_qt_commande         = fields.Float("Qt Commande"       , digits=(14,2), related='is_sale_line_id.product_uom_qty')
    is_facturable_pourcent = fields.Float("% facturable"      , digits=(14,2))
    is_a_facturer          = fields.Float("A Facturer"        , digits=(14,2), help="Montant à facturer sur cette facture")

# -*- coding: utf-8 -*-
from odoo import models,fields,api


class AccountMove(models.Model):
    _inherit = "account.move"

    is_order_id   = fields.Many2one('sale.order', 'Commande')
    is_affaire_id = fields.Many2one('is.affaire', 'Affaire', related='is_order_id.is_affaire_id')

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



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_affaire_id   = fields.Many2one('is.affaire', 'Affaire')
    is_sale_line_id = fields.Many2one('sale.order.line', 'Ligne de commande')


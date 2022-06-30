# -*- coding: utf-8 -*-
from odoo import models,fields,api

class purchase_order(models.Model):
    _inherit = "purchase.order"

    is_condition_tarifaire = fields.Text('Conditions tarifaire', related='partner_id.is_condition_tarifaire')


class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"

    is_largeur = fields.Float('Largeur')
    is_hauteur = fields.Float('Hauteur')


    @api.onchange('is_largeur','is_hauteur')
    def onchange_calculateur(self):
        for obj in self:
            print(obj)
            if  obj.is_largeur and obj.is_hauteur:
                obj.product_qty = obj.is_largeur*obj.is_hauteur

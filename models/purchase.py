# -*- coding: utf-8 -*-
from odoo import models,fields,api

class purchase_order(models.Model):
    _inherit = "purchase.order"

    is_condition_tarifaire = fields.Text('Conditions tarifaire', related='partner_id.is_condition_tarifaire')

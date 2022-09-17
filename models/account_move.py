# -*- coding: utf-8 -*-
from odoo import models,fields,api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_affaire_id = fields.Many2one('is.affaire', 'Affaire')


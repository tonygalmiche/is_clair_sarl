# -*- coding: utf-8 -*-
from odoo import fields, models


class product_template(models.Model):
    _inherit = "product.template"
    _order="name"

    is_tache = fields.Boolean("Tache")

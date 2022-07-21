# -*- coding: utf-8 -*-
from itertools import product
from odoo import models,fields,api
from odoo.tools.misc import formatLang, get_lang

class purchase_order(models.Model):
    _inherit = "purchase.order"

    is_affaire_id     = fields.Many2one('is.affaire', 'Affaire')
    is_date           = fields.Date('Date')
    is_delai          = fields.Date('Délai')
    is_date_livraison = fields.Date('Date de livraison')
    is_lieu_livraison = fields.Selection([
        ('notre_adresse', 'A notre adresse'),
        ('chantier'     , 'Livraison sur chantier référence'),
    ], 'Lieu de livraison')
    is_condition_tarifaire = fields.Text('Conditions tarifaire', related='partner_id.is_condition_tarifaire')


class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"

    is_finition_id   = fields.Many2one('is.finition'  , 'Finition')
    is_traitement_id = fields.Many2one('is.traitement', 'Traitement')
    is_largeur       = fields.Float('Largeur')
    is_hauteur       = fields.Float('Hauteur')

    @api.onchange('is_largeur','is_hauteur')
    def onchange_calculateur(self):
        for obj in self:
            print(obj)
            if  obj.is_largeur and obj.is_hauteur:
                obj.product_qty = obj.is_largeur*obj.is_hauteur


    @api.onchange('product_id','is_finition_id','is_traitement_id')
    def _product_id_change(self):
        if not self.product_id:
            return
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        name = "%s %s %s"%(self.product_id.name, (self.is_finition_id.name or ''), (self.is_traitement_id.name or ''))
        self.name = name
        #self.name = self._get_product_purchase_description(product_lang)
        self._compute_tax_id()


class IsFinition(models.Model):
    _name='is.finition'
    _description = "Finition"
    _order='name'

    name = fields.Char('Finition', required=True, index=True)


class IsTraitement(models.Model):
    _name='is.traitement'
    _description = "Traitement"
    _order='name'

    name = fields.Char('Traitement', required=True, index=True)

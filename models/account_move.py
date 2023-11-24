# -*- coding: utf-8 -*-
from odoo import models,fields,api


class AccountMove(models.Model):
    _inherit = "account.move"

    is_order_id         = fields.Many2one('sale.order', 'Commande')
    #is_affaire_id       = fields.Many2one('is.affaire', 'Affaire', related='is_order_id.is_affaire_id')
    is_affaire_id       = fields.Many2one('is.affaire', 'Affaire', compute='_compute_is_affaire_id', store=True, readonly=True)
    is_banque_id        = fields.Many2one('account.journal', 'Banque par défaut', related='partner_id.is_banque_id')
    is_export_compta_id = fields.Many2one('is.export.compta', 'Folio', copy=False)
    is_courrier_id      = fields.Many2one('is.courrier.expedie', 'Courrier expédié', copy=False)
    is_traite_id        = fields.Many2one('is.traite', 'Traite')
    is_situation        = fields.Char("Situation")
    is_a_facturer       = fields.Monetary("Total à facturer", currency_field='currency_id', store=True, readonly=True, compute='_compute_is_a_facturer')
    is_facture          = fields.Monetary("Total facturé"   , currency_field='currency_id', store=True, readonly=True, compute='_compute_is_a_facturer', help="Montant total facturé hors remises")
    is_attente_avoir    = fields.Char("Attente avoir", help="Motif de l'attente de l'avoir")


    @api.depends('is_order_id','purchase_id','invoice_line_ids','state')
    def _compute_is_affaire_id(self):
        for obj in self:
            affaire_id = False
            if obj.purchase_id and obj.purchase_id.is_affaire_id:
                affaire_id = obj.purchase_id.is_affaire_id.id
            if obj.is_order_id and obj.is_order_id.is_affaire_id:
                affaire_id = obj.is_order_id.is_affaire_id.id
            if not affaire_id:
                for line in obj.invoice_line_ids:
                    if line.is_affaire_id:
                        affaire_id = line.is_affaire_id.id
                        break
            print(obj.name, affaire_id)
            obj.is_affaire_id = affaire_id


    @api.depends('invoice_line_ids','state')
    def _compute_is_a_facturer(self):
        for obj in self:
            is_a_facturer = 0
            is_facture = 0
            for line in obj.invoice_line_ids:
                is_a_facturer+=line.is_a_facturer
                if line.is_facturable_pourcent!=0:
                    is_facture+=line.price_subtotal
            obj.is_a_facturer = is_a_facturer
            obj.is_facture    = is_facture


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


    def enregistre_courrier_action(self):
        for obj in self:
            vals={
                "partner_id": obj.partner_id.id,
                "affaire_id": obj.is_affaire_id.id,
                "invoice_id": obj.id,
                "objet"     : "Facture client",
                "montant"   : obj.amount_untaxed_signed,
            }
            courrier = self.env['is.courrier.expedie'].create(vals)
            obj.is_courrier_id = courrier.id


    def initialiser_affaire_action(self):
        for obj in self:
            if obj.is_affaire_id:
                for line in obj.invoice_line_ids:
                    if not line.is_affaire_id:
                        line.is_affaire_id = obj.is_affaire_id.id
                        print(obj.name,line)



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_affaire_id   = fields.Many2one('is.affaire', 'Affaire')
    is_sale_line_id = fields.Many2one('sale.order.line', 'Ligne de commande', index=True)
    is_qt_commande         = fields.Float("Qt Commande"       , digits=(14,2), related='is_sale_line_id.product_uom_qty')
    is_facturable_pourcent = fields.Float("% facturable"      , digits=(14,2))
    is_a_facturer          = fields.Float("A Facturer"        , digits=(14,2), help="Montant à facturer sur cette facture")

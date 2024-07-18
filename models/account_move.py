# -*- coding: utf-8 -*-
from odoo import models,fields,api
from dateutil.relativedelta import relativedelta


class is_account_move_section(models.Model):
    _name='is.account.move.section'
    _description = "Sections des factures"
    _rec_name = 'section_id'
    _order='sequence'

    move_id          = fields.Many2one('account.move', 'Facture', required=True, ondelete='cascade')
    section_id       = fields.Many2one('is.sale.order.section', 'Section', index=True)
    sequence         = fields.Integer("Sequence")
    currency_id      = fields.Many2one(related='move_id.currency_id')
    facture          = fields.Monetary("Montant Facturé", currency_field='currency_id')
    facture_pourcent = fields.Float("% Facturé", digits=(14,2))


class is_account_move_remise(models.Model):
    _name='is.account.move.remise'
    _description = "Remises après le TTC (Retenue de garantie)"

    move_id          = fields.Many2one('account.move', 'Facture', required=True, ondelete='cascade')
    product_id       = fields.Many2one('product.product', 'Remise', index=True)
    libelle          = fields.Text("Libellé")
    currency_id      = fields.Many2one(related='move_id.currency_id')
    montant          = fields.Monetary("Montant", currency_field='currency_id')


class AccountMove(models.Model):
    _inherit = "account.move"
    _order='name desc'

    is_order_id          = fields.Many2one('sale.order', 'Commande')
    is_date_pv           = fields.Date(related='is_order_id.is_date_pv')
    is_affaire_id        = fields.Many2one('is.affaire', 'Affaire', compute='_compute_is_affaire_id', store=True, readonly=True)
    is_banque_id         = fields.Many2one('account.journal', 'Banque par défaut', related='partner_id.is_banque_id')
    is_export_compta_id  = fields.Many2one('is.export.compta', 'Folio', copy=False)
    is_courrier_id       = fields.Many2one('is.courrier.expedie', 'Courrier expédié', copy=False)
    is_traite_id         = fields.Many2one('is.traite', 'Traite')
    is_situation         = fields.Char("Situation (Titre)")
    is_a_facturer        = fields.Monetary("Total à facturer", currency_field='currency_id', store=True, readonly=True, compute='_compute_is_a_facturer')
    is_facture           = fields.Monetary("Total facturé"   , currency_field='currency_id', store=True, readonly=True, compute='_compute_is_a_facturer', help="Montant total facturé hors remises")
    is_attente_avoir     = fields.Char("Attente avoir", help="Motif de l'attente de l'avoir")
    active               = fields.Boolean("Active", store=True, readonly=True, compute='_compute_active')
    is_montant_paye      = fields.Monetary(string='Montant payé', store=True, readonly=True, compute='_compute_is_montant_paye', currency_field='company_currency_id')
    is_pourcent_du       = fields.Float(string='% dû'           , store=True, readonly=True, compute='_compute_is_montant_paye')
    is_echeance_1an      = fields.Date("Échéance 1an"           , store=True, readonly=True, compute='_compute_is_montant_paye')
    is_remarque_paiement = fields.Char("Remarque paiememt")
    is_motif_avoir       = fields.Char("Motif avoir")
    active               = fields.Boolean("Active", store=True, readonly=True, compute='_compute_active')
    is_purchase_order_id = fields.Many2one('purchase.order', 'Commande fournisseur', compute='_compute_is_purchase_order_id', store=False, readonly=True)
    is_type_paiement     = fields.Selection(related='partner_id.is_type_paiement')
    is_section_ids       = fields.One2many('is.account.move.section', 'move_id', 'Sections', readonly=True)
    is_remise_ids        = fields.One2many('is.account.move.remise' , 'move_id', 'Remises' , readonly=True)
    is_reste_du_ttc      = fields.Monetary(string='Reste dû TTC', store=True, readonly=True, compute='_compute_is_montant_paye', currency_field='company_currency_id')
    is_date_relance      = fields.Date(string='Date dernière relance', readonly=1)
    is_date_releve       = fields.Date(string='Date dernier relevé'  , readonly=1)
    is_date_envoi        = fields.Date(string="Date d'envoi", help="Date d'envoi de la facture par mail")
    # is_courriel_facturation = fields.Char(related="partner_id.is_courriel_facturation")


    @api.depends('state')
    def _compute_is_purchase_order_id(self):
        for obj in self:
            purchase_id = False
            for line in obj.invoice_line_ids:
                if line.purchase_line_id:
                    purchase_id = line.purchase_line_id.order_id.id
            obj.is_purchase_order_id=purchase_id


    @api.depends('state','amount_total_signed','amount_residual_signed','invoice_date','is_order_id', 'is_order_id.is_date_pv')
    def _compute_is_montant_paye(self):
        for obj in self:
            montant = obj.amount_total_signed-obj.amount_residual_signed
            obj.is_montant_paye = montant
            pourcent=0
            if obj.amount_total_signed!=0:
                pourcent = 100*obj.amount_residual_signed / obj.amount_total_signed
            obj.is_pourcent_du  = pourcent
            echeance=False
            if obj.is_order_id.is_date_pv:
                echeance=obj.is_order_id.is_date_pv
            else:
                if obj.invoice_date:
                    echeance=obj.invoice_date   
            if echeance:
                echeance += relativedelta(years=1)
            obj.is_echeance_1an = echeance
            remise = 0
            for line in obj.is_remise_ids:
                remise+=line.montant
            obj.is_reste_du_ttc = obj.amount_total - remise


    @api.depends('state')
    def _compute_active(self):
        for obj in self:
            active=True
            if obj.state=='cancel':
                active = False
            obj.active = active
            obj.initialiser_sections_facture_action()


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


    def initialiser_compte_vente_action(self):
        for obj in self:
            for line in obj.invoice_line_ids:
                if line.product_id:
                    accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=obj.fiscal_position_id)
                    account_id = accounts['income'].id
                    line.account_id = account_id


    def initialiser_paiement_traite_action(self):
        for obj in self:
            if obj.state=='posted' and obj.move_type in ('in_invoice','in_refund'):
                if obj.payment_state=='not_paid' and obj.is_traite_id.id:
                    obj.sudo().payment_state='paid'
                    obj.sudo().amount_residual=0
                if obj.payment_state=='paid' and obj.is_traite_id.id==False and obj.invoice_payments_widget=='false':
                    obj.sudo().payment_state='not_paid'
                    obj.sudo()._compute_amount()


    def initialiser_sections_facture_action(self):
        for obj in self:
            if type(obj.id)==int:
                sections={}
                for line in obj.invoice_line_ids:
                    section = line.is_section_id
                    if section:
                        if section not in sections:
                            sections[section]={'montant_cde':0, 'montant_fac':0}
                        sections[section]['montant_cde']+=line.is_montant_cde
                        sections[section]['montant_fac']+=line.price_subtotal
                        #sections[section]['montant_fac']+=line.is_a_facturer
                obj.is_section_ids.unlink()
                for section in sections:
                    facture_pourcent = facture = 0
                    if sections[section]['montant_cde']!=0:
                        facture          = sections[section]['montant_fac']
                        facture_pourcent = 100 * sections[section]['montant_fac'] / sections[section]['montant_cde']
                    vals={
                        'move_id'         : obj.id,
                        'sequence'        : section.sequence,
                        'section_id'      : section.id,
                        'facture'         : facture,
                        'facture_pourcent': facture_pourcent,
                    }
                    self.env['is.account.move.section'].create(vals)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_affaire_id          = fields.Many2one('is.affaire', 'Affaire')
    is_sale_line_id        = fields.Many2one('sale.order.line', 'Ligne de commande', index=True)
    is_section_id          = fields.Many2one(related='is_sale_line_id.is_section_id')
    is_qt_commande         = fields.Float("Qt Cde", digits=(14,2), related='is_sale_line_id.product_uom_qty')
    is_montant_cde         = fields.Monetary("Montant Cde", related='is_sale_line_id.price_subtotal' )# currency_field='currency_id', store=False, readonly=True, compute='_compute_montant')
    is_facturable_pourcent = fields.Float("% Facturable"      , digits=(14,2))
    is_a_facturer          = fields.Float("A Facturer"        , digits=(14,2), help="Montant à facturer sur cette facture")
    is_famille_id          = fields.Many2one('is.famille', related='product_id.is_famille_id')

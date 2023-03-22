# -*- coding: utf-8 -*-
from odoo import models,fields,api

class IsTraite(models.Model):
    _name='is.traite'
    _description = "Traite"
    _order='date_retour desc'
    _rec_name='date_retour'

    date_retour    = fields.Date('Date de retour', required=True, index=True, default=fields.Date.context_today)
    partner_id     = fields.Many2one('res.partner' , 'Fournisseur', required=True)
    montant        = fields.Float("Montant", digits=(14,2), store=True, readonly=True, compute='_compute_montant')
    date_reglement = fields.Date('Date de règlement', store=True, readonly=True, compute='_compute_montant')
    is_courrier_id = fields.Many2one('is.courrier.expedie', 'Courrier expédié', copy=False)
    ligne_ids      = fields.One2many('account.move', 'is_traite_id', 'Lignes')


    @api.depends('ligne_ids')
    def _compute_montant(self):
        for obj in self:
            montant = 0
            date_reglement = False
            for line in obj.ligne_ids:
                montant+=line.amount_total_signed
                date_reglement = line.invoice_date_due
            obj.montant        = montant
            obj.date_reglement = date_reglement


    def enregistre_courrier_action(self):
        for obj in self:
            objet="Traite retournée le %s en réglement du %s"%(obj.date_retour.strftime('%d/%m/%Y'),obj.date_reglement.strftime('%d/%m/%Y'))
            vals={
                "partner_id": obj.partner_id.id,
                "objet"     : objet,
                "montant"   : obj.montant,
                "traite_id" : obj.id,
            }
            courrier = self.env['is.courrier.expedie'].create(vals)
            obj.is_courrier_id = courrier.id


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_num_cheque  = fields.Char("Mode de règlement", help="N° du chèque")
    is_courrier_id = fields.Many2one('is.courrier.expedie', 'Courrier expédié', copy=False)


    def enregistre_courrier_action(self):
        for obj in self:
            objet="Règlement %s %s"%(obj.ref, (obj.is_num_cheque or ''))
            vals={
                "partner_id": obj.partner_id.id,
                "payment_id": obj.id,
                "objet"     : objet,
                "montant"   : obj.amount,
            }
            courrier = self.env['is.courrier.expedie'].create(vals)
            obj.is_courrier_id = courrier.id


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    is_num_cheque = fields.Char("Mode de règlement", help="N° du chèque")


    def _create_payment_vals_from_wizard(self):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
        payment_vals["is_num_cheque"] = "%s sur %s"%(self.is_num_cheque,self.journal_id.name)
        # for obj in self:
        #     objet="Règlement %s %s"%(self.communication, payment_vals["is_num_cheque"])
        #     vals={
        #         "partner_id": payment_vals["partner_id"],
        #         "objet"     : objet,
        #         "montant"   : payment_vals["amount"],
        #     }
        #     courrier = self.env['is.courrier.expedie'].create(vals)
        return payment_vals

# -*- coding: utf-8 -*-
from odoo import models,fields,api


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_num_cheque = fields.Char("Mode de règlement", help="N° du chèque")


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    is_num_cheque = fields.Char("Mode de règlement", help="N° du chèque")


    def _create_payment_vals_from_wizard(self):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
        payment_vals["is_num_cheque"] = self.is_num_cheque
        for obj in self:
            objet="Règlement %s %s"%(self.communication, payment_vals["is_num_cheque"])
            vals={
                "partner_id": payment_vals["partner_id"],
                "objet"     : objet,
                "montant"   : payment_vals["amount"],
            }
            courrier = self.env['is.courrier.expedie'].create(vals)
        return payment_vals

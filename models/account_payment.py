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
        print(payment_vals)
        payment_vals["is_num_cheque"] = self.is_num_cheque
        return payment_vals



        # payment_vals = {
        #     'date': self.payment_date,
        #     'amount': self.amount,
        #     'payment_type': self.payment_type,
        #     'partner_type': self.partner_type,
        #     'ref': self.communication,
        #     'journal_id': self.journal_id.id,
        #     'currency_id': self.currency_id.id,
        #     'partner_id': self.partner_id.id,
        #     'partner_bank_id': self.partner_bank_id.id,
        #     'payment_method_line_id': self.payment_method_line_id.id,
        #     'destination_account_id': self.line_ids[0].account_id.id
        # }

        # if not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
        #     payment_vals['write_off_line_vals'] = {
        #         'name': self.writeoff_label,
        #         'amount': self.payment_difference,
        #         'account_id': self.writeoff_account_id.id,
        #     }
        # return payment_vals

# coding: utf-8
import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

class AccountPayment(models.Model):
    _inherit = "account.payment"

    amount_aliquot_in_words = fields.Char(string="Amount in Words")
    is_withholding = fields.Boolean("Withholding", default=False)
    type_aliquot = fields.Selection([('none', ''), ('earnings', 'Earnings')], string="Type aliquot", default='none')
    withholding_receipt = fields.Char("Withholding Receipt")
    customers_withholding = fields.Boolean(related='journal_id.is_withholding',  string="Withholding", default=False)

    def _convert_payment(self, currency, from_amount, to_currency, company, date, divide=False):
        return currency._convert(from_amount, to_currency, company, date)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.type_aliquot != 'none' and rec.payment_group_id.is_canceled:
                raise UserError(_('You cannot delete a payment with declared withholdings.'))
        res = super(AccountPayment, self).unlink()
        return res

    @api.multi
    @api.constrains('communication')
    def _check_uniq_circular(self):
        if self.is_withholding:
            super(AccountPayment, self.with_context({'not_uniq_cir': True}))._check_uniq_circular()
        else:
            super(AccountPayment, self)._check_uniq_circular()

# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)

class L10nArAccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends('amount_total', 'residual', 'amount_untaxed', 'group_invoice_ids', 'group_invoice_ids.withholding_tax_real')
    def _compute_no_withholding_amount_iibb(self):
        base_withholding = self._calculate_base_withholding()
        self.no_withholding_amount_iibb = (self.amount_untaxed - base_withholding) * -1 if self.refund_type == 'credit' and self.type in ['in_refund','out_refund'] else (self.amount_untaxed - base_withholding)

        #if self.amount_total  - self.residual >= self.neto_gravado:
            #self.no_withholding_amount_iibb = 0.0
        #else:
            #self.no_withholding_amount_iibb = self.neto_gravado - (self.amount_total  - self.residual)

    no_withholding_amount_iibb = fields.Monetary(string='Withholding IIBB', copy=False, store=True, readonly=True,
                        compute='_compute_no_withholding_amount_iibb', track_visibility='always',
                        digits=dp.get_precision('Account'))

    group_invoice_ids = fields.One2many('account.payment.group.invoice', 'invoice_id', string='Payment')

    def _calculate_base_withholding(self):
        base_withholding = 0.0
        #payment_group= self.payment_move_line_ids.mapped('payment_id.payment_group_id')
        #if payment_group:
            #refs = set(payment_group.mapped('id'))
            #sql_query = """SELECT withholding_tax_base
            #                FROM account_payment_group P
            #                WHERE P.id in %s"""
            #params = (tuple(refs),)
            #self.env.cr.execute(sql_query, params)
            #results = self.env.cr.dictfetchall()
            #for line in results:
            #    base_withholding += line.get('withholding_tax_base')
        base_withholding += sum(x.withholding_tax_real for x in self.payment_move_line_ids.mapped(
                                                            'payment_id.payment_group_id.group_invoice_ids').filtered(
                                                            lambda x: x.invoice_id == self))
        base_withholding += sum(x.amount_untaxed for x in self.payment_move_line_ids.mapped('invoice_id'))
        return base_withholding

    def _convert_invoice(self, currency, from_amount, to_currency, company, date, divide=False):
        return currency._convert(from_amount, to_currency, company, date)

    @api.multi
    def assign_outstanding_credit(self, credit_aml_id, payment=0):
        self.ensure_one()
        res = super(L10nArAccountInvoice, self).assign_outstanding_credit(credit_aml_id, payment)
        if payment == 1:
            payment_group_id = self.env['account.payment.group'].browse(credit_aml_id)
            payment_group_id._create_group_invoice_ids(self)
        return res

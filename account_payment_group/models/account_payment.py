# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from ast import literal_eval
from lxml import etree
from odoo.tools.safe_eval import safe_eval

from itertools import groupby

MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': -1,
    'in_invoice': -1,
    'out_refund': 1,
}


class AccountPayment(models.Model):
    _inherit = "account.payment"
    _order = "payment_date asc, name asc"

    def _default_journal_id(self):
        if not (self._context.get('default_payment_type', False) == 'transfer' and (
                self._context.get('journal_id', False) or
                self._context.get('default_journal_id', False))):
            journal = self.env['account.journal'].search(
                [('type', 'in', ('bank', 'cash')),
                 ('currency_id', '=', self._context.get('default_currency_id', False))], limit=1)
            if journal:
                return journal.id

    payment_group_id = fields.Many2one('account.payment.group', 'Payment Group', ondelete='cascade', readonly=True,
                                       translate=True)
    payment_group_company_id = fields.Many2one(related='payment_group_id.company_id')
    payment_type_copy = fields.Selection(selection=[('outbound', 'Send Money'), ('inbound', 'Receive Money')],
                                         compute='_compute_payment_type_copy', inverse='_inverse_payment_type_copy',
                                         string='Payment Type')
    amount_company_currency = fields.Monetary(string='Payment Amount on Company Currency',
                                              currency_field='company_currency_id', translate=True,
                                              compute='_compute_amount_company_currency')
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    # currency_rate = fields.Float(string='currency_rate')
    # manual_currency_rate = fields.Float(string='manual_currency_rate')
    # tot_in_currency = fields.Float(string='manual_currency_rate')
    currency2_id = fields.Many2one('res.currency', 'Currency', readonly=False)
    # manual_currency_rate_active = fields.Boolean(string='manual_currency_rate', default=False)
    date_emission = fields.Datetime('Emission Date', default=fields.Datetime.now)
    payment_difference_amount = fields.Monetary(readonly=False)
    amount = fields.Monetary(string='Payment Amount', required=True,
                             default=lambda self: self._context.get('default_amount') if self._context.get(
                                 'default_amount', False) else 0.0)
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True,
                                 domain=[('type', 'in', ('bank', 'cash'))],
                                 default=lambda self: self._default_journal_id())

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountPayment, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                          submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='journal_id']"):
                domain = safe_eval(node.get('domain', '[]'))
                if self._context.get('journal_id', False):
                    domain.append(('id', '=', self._context.get('journal_id')))
                    node.set('domain', repr(domain))
            res['arch'] = etree.tostring(doc)
        return res

    @api.one
    @api.depends('amount', 'currency_id', 'company_id.currency_id')
    def _compute_amount_company_currency(self):
        payment_currency = self.currency_id
        company_currency = self.company_id.currency_id or self.payment_group_company_id.currency_id
        company = self.company_id or self.payment_group_company_id
        if payment_currency and payment_currency != company_currency:
            # amount_company_currency = self.currency_id.with_context(
            #     date=self.payment_date).compute(
            #         self.amount, self.company_id.currency_id)
            amount_company_currency = self.currency_id._convert(self.amount,
                                                       company_currency, company,
                                                       self.payment_date or fields.Date.today())
        else:
            amount_company_currency = self.amount
        sign = 1.0
        if (
                (self.partner_type == 'supplier' and
                 self.payment_type == self.payment_type == 'inbound') or
                (self.partner_type == 'customer' and
                 self.payment_type == self.payment_type == 'outbound')):
            sign = -1.0
        self.amount_company_currency = amount_company_currency * sign

    @api.multi
    @api.onchange('payment_type_copy')
    def _inverse_payment_type_copy(self):
        for rec in self:
            rec.payment_type = (
                    rec.payment_type_copy and rec.payment_type_copy or 'transfer')

    @api.multi
    @api.depends('payment_type')
    def _compute_payment_type_copy(self):
        for rec in self:
            if rec.payment_type == 'transfer':
                continue
            rec.payment_type_copy = rec.payment_type

    @api.multi
    def get_journals_domain(self):
        domain = super(AccountPayment, self).get_journals_domain()
        if self.payment_group_company_id:
            domain.append(
                ('company_id', '=', self.payment_group_company_id.id))
        return domain

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if not self._context.get('payment_group'):
            return super(AccountPayment, self)._onchange_payment_type()

    @api.multi
    @api.constrains('payment_group_id', 'payment_type')
    def check_payment_group(self):
        if literal_eval(self.env['ir.config_parameter'].get_param(
                'enable_payments_without_payment_group', 'False')):
            return True
        for rec in self:
            if rec.payment_type == 'transfer':
                if rec.payment_group_id:
                    pass
            else:
                if not rec.payment_group_id:
                    pass

    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, currency_id = aml_obj.with_context(
            date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)

        move = self.env['account.move'].create(self._get_move_vals())

        # Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        # Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference_amount:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(
                date=self.payment_date)._compute_amount_fields(self.payment_difference_amount, self.currency_id,
                                                               self.company_id.currency_id)
            writeoff_line['name'] = self.writeoff_label
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit'] or (writeoff_line['credit'] and not counterpart_aml['credit']):
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit'] or (writeoff_line['debit'] and not counterpart_aml['debit']):
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo

        # Write counterpart lines
        if not self.currency_id.is_zero(self.amount):
            if not self.currency_id != self.company_id.currency_id:
                amount_currency = 0
            liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
            liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
            aml_obj.create(liquidity_aml_dict)

        # validate the payment
        if not self.journal_id.post_at_bank_rec:
            move.post()

        # reconcile the invoice receivable/payable line(s) with the payment
        if self.invoice_ids and not self._context.get('no_reconcile', False):
            self.invoice_ids.register_payment(counterpart_aml)

        return move

    @api.onchange('amount', 'currency_id')
    def _onchange_amount(self):
        is_init = False
        if self.amount == 0.0 and self.amount != self.payment_group_id.amount_payable:
            self.amount = self.payment_group_id.payment_difference
            is_init = True

        jrnl_filters = self._compute_journal_domain_and_types()
        journal_types = jrnl_filters['journal_types']
        domain_on_types = [('type', 'in', list(journal_types))]
        if self.journal_id.type not in journal_types and not is_init and self.currency_id == self.payment_group_id.company_id.currency_id:
            self.journal_id = self.env['account.journal'].search(domain_on_types, limit=1)
        return {'domain': {'journal_id': jrnl_filters['domain'] + domain_on_types}}

    @api.onchange('currency_id')
    def _onchange_currency(self):
        self.amount = abs(self._compute_payment_amount(currency=self.currency_id, amount=self.amount))

        # Set by default the first liquidity journal having this currency if exists.
        if (self.journal_id.currency_id and self.journal_id.currency_id != self.currency_id) or (
                not self.journal_id.currency_id and self.currency_id != self.company_id.currency_id):
            journal = self.env['account.journal'].search(
                [('type', 'in', ('bank', 'cash')), ('currency_id', '=', self.currency_id.id)], limit=1)
            if journal:
                self.journal_id = journal.id
            else:
                self.journal_id = self.env['account.journal']

    @api.multi
    def _compute_payment_amount(self, invoices=None, currency=None, amount=None):
        # Get the payment invoices
        if not invoices:
            invoices = self.invoice_ids

            # Get the payment currency
        if not currency:
            currency = self.currency_id or self.journal_id.currency_id or self.journal_id.company_id.currency_id or invoices and \
                       invoices[0].currency_id

            # Get the payment currency
        if not amount:
            amount = self.amount

        if self.currency2_id and self.currency2_id != currency:
            total = self.currency2_id._convert(amount, currency, self.env.user.company_id,
                                               self.payment_date or fields.Date.today())
            self.currency2_id = currency
            return total
        return amount

        # Avoid currency rounding issues by summing the amounts according to the company_currency_id before
        # total = 0.0
        # groups = groupby(invoices, lambda i: i.currency_id)
        # for payment_currency, payment_invoices in groups:
        #     amount_total = sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.residual_signed for i in payment_invoices])
        #     if payment_currency == currency:
        #         total += amount_total
        #     else:
        #         total += payment_currency._convert(amount_total, currency, self.env.user.company_id,
        #                                            self.payment_date or fields.Date.today())
        # return total

    @api.one
    def get_amount_currency(self):
        if self.company_id.currency_id != self.currency_id:
            # return self.currency_id.with_context(date=self.payment_date).compute(
            #             self.amount, self.company_id.currency_id)
            return self.currency_id._convert(self.amount, self.company_id.currency_id, self.company_id,
                                             self.payment_date or fields.Date.today())
        else:
            return self.amount

    @api.multi
    @api.constrains('communication')
    def _check_uniq_circular(self):
        for payment in self:
            if payment.communication and not self._context.get('not_uniq_cir'):
                payments = self.env['account.payment'].search(
                    [('communication', '=', payment.communication), ('journal_id', '=', payment.journal_id.id),
                     ('company_id', '=', payment.company_id.id),
                     ('payment_type', '=', payment.payment_type), ('id', '!=', payment.id)])
                if payments:
                    raise ValidationError(_(
                        'The number of the circular must be unique'))


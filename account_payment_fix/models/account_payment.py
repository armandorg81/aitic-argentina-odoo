# -*- coding: utf-8 -*-
from odoo import fields, models, api
# from openerp.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    payment_method_ids = fields.Many2many(
        'account.payment.method',
        compute='_compute_payment_methods'
    )
    journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_journals'
    )
    destination_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_destination_journals'
    )

    @api.multi
    @api.depends(
        # 'payment_type',
        'journal_id',
    )
    def _compute_destination_journals(self):
        for rec in self:
            domain = [
                ('type', 'in', ('bank', 'cash')),
                ('company_id', '=', rec.journal_id.company_id.id),
            ]
            rec.destination_journal_ids = rec.journal_ids.search(domain)


    @api.multi
    def get_journals_domain(self):
        """
        We get domain here so it can be inherited
        """
        self.ensure_one()
        domain = [('type', 'in', ('bank', 'cash'))]
        if self.payment_type == 'inbound':
            domain.append(('at_least_one_inbound', '=', True))
        else:
            domain.append(('at_least_one_outbound', '=', True))
        return domain

    @api.multi
    @api.depends(
        'payment_type',
    )
    def _compute_journals(self):
        for rec in self:
            rec.journal_ids = rec.journal_ids.search(rec.get_journals_domain())

    @api.multi
    @api.depends(
        'journal_id.outbound_payment_method_ids',
        'journal_id.inbound_payment_method_ids',
        'payment_type',
    )
    def _compute_payment_methods(self):
        for rec in self:
            if rec.payment_type in ('outbound', 'transfer'):
                methods = rec.journal_id.outbound_payment_method_ids
            else:
                methods = rec.journal_id.inbound_payment_method_ids
            rec.payment_method_ids = methods.ids

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if not self.invoice_ids:
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'
        if self.payment_method_ids:
            return {'domain': {'payment_method_id': [('id', 'in', self.payment_method_ids.ids)]}}
        else:
            return {}

    # @api.onchange('partner_type')
    def _onchange_partner_type(self):
        """
        Agregasmos dominio en vista ya que se pierde si se vuelve a entrar
        Anulamos funcion original porque no haria falta
        """
        return True

    @api.onchange('journal_id')
    def _onchange_journal(self):
        payment_methods = self.env['account.payment.method']
        if self.journal_id:
            self.currency_id = (
                self.journal_id.currency_id or self.company_id.currency_id)
            payment_methods = (
                self.payment_type == 'inbound' and
                self.journal_id.inbound_payment_method_ids or
                self.journal_id.outbound_payment_method_ids)
            self.payment_method_id = (
                payment_methods and payment_methods[0] or False)
        if self.journal_ids:
            return {'domain': {
                        'journal_id': [('id', 'in', self.journal_ids.ids)],
                        'destination_journal_id': [('id', 'in', self.destination_journal_ids.ids)],
                        'payment_method_id': [('id', 'in', payment_methods.ids)]
                    }}
        else:
            return {}

    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        res = super(AccountPayment, self)._compute_destination_account_id()
        if not self.invoice_ids and self.payment_type != 'transfer':
            partner = self.partner_id.with_context(
                force_company=self.company_id.id)
            if self.partner_type == 'customer':
                self.destination_account_id = (
                    partner.property_account_receivable_id.id)
            else:
                self.destination_account_id = (
                    partner.property_account_payable_id.id)
        return res

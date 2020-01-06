# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class account_check_action_wizard(models.TransientModel):
    _name = 'account.check.action.wizard'
    _description = 'Account Check Action Wizard'

    @api.model
    def _default_product(self):
        if self._context.get('default_partner_id'):
            partner_id = self.env['res.partner'].browse(self._context.get('default_partner_id'))
            if partner_id.supplier:
                return True
        return False

    @api.model
    def _default_partner_id(self):
        if self._context.get('default_partner_id', False):
            return self._context.get('default_partner_id')
        if self._context.get('default_check_ids', False):
            check_ids = self.env['account.check'].browse(self._context.get('default_check_ids'))
            return check_ids[0].operation_partner_id.id
        return self.env['res.partner']

    @api.model
    def _default_amount(self):
        if self._context.get('default_check_ids', False):
            check_ids = self.env['account.check'].browse(self._context.get('default_check_ids'))
            return sum(x.amount for x in self.check_ids)
        return 0.0

    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )
    partner_id = fields.Many2one('res.partner', string='Partner', default=_default_partner_id)
    debit_note = fields.Boolean(string='Debit note', default=_default_product)
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 domain=[('type', 'in', ['cash', 'bank'])])
    expense_check_account_id = fields.Many2one(
        'account.account',
        'Account Expense',
        domain=lambda self: [('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id)]
    )
    amount = fields.Monetary(currency_field='company_currency_id', string='Expense amount', default=_default_amount)
    amount_total = fields.Monetary(currency_field='company_currency_id', string='Amount total', compute='_compute_calcular_amount_total')

    communication = fields.Char(string='Memo')

    company_id = fields.Many2one(related='journal_id.company_id', readonly=True, store=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    action_type = fields.Char(
        'Action type passed on the context',
        required=True,
    )
    check_ids = fields.Many2many(
        'account.check',
        string='Checks',
        copy=False
    )
    tax_ids = fields.Many2many('account.tax', 'account_check_action_tax', 'account_check_action_id', 'tax_id',
                                    string='Taxes',
                                    domain=[('type_tax_use', '=', 'purchase'), '|', ('active', '=', False),
                                            ('active', '=', True)])

    @api.one
    @api.depends('check_ids')
    def _compute_calcular_amount_total(self):
        if self.check_ids:
            self.amount_total = sum(x.amount for x in self.check_ids)
        else:
            self.amount_total = 0.0

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        if self.action_type not in [
                'use', 'claim', 'bank_debit', 'reject', 'negotiated', 'selled', 'customer_return', 'reject_holding', 'deposited', 'reject_holding']:
            raise ValidationError(_(
                'Action %s not supported on checks') % self.action_type)
        check = self.env['account.check'].browse(
            self._context.get('active_id'))
        journal_type = ''
        if self.action_type in ['customer_return','claim']:
            journal_type = 'sale'
        if self.action_type == 'selled':
            #if self.amount <= 0.0:
                #raise ValidationError(_(
                    #'Action %s not supported on checks') % self.action_type)
            if self.check_ids:
                return getattr(self.check_ids.with_context(action_date=self.date, partner=self.partner_id.id,
                                                  expense_amount=self.amount, debit_note=self.debit_note,
                                                  journal_type=journal_type,
                                                  journal=self.journal_id.id,
                                                  expense_account=self.expense_check_account_id.id,
                                                  tax_ids=self.tax_ids.ids if self.tax_ids else False,
                                                  check_ids=self.check_ids.ids), self.action_type)()
            else:
                return getattr(check.with_context(action_date=self.date, partner=self.partner_id.id,
                                                  expense_amount=self.amount, debit_note=self.debit_note,
                                                  journal_type=journal_type,
                                                  journal=self.journal_id.id,
                                                  expense_account=self.expense_check_account_id.id,
                                                  tax_ids=self.tax_ids.ids if self.tax_ids else False), self.action_type)()
        if self.action_type == 'negotiated':
            if self.check_ids:
                return getattr(
                    self.check_ids.with_context(action_date=self.date, partner=self.partner_id.id,
                                                  journal_type=journal_type,
                                                  tax_ids=self.tax_ids.ids if self.tax_ids else False), self.action_type)()
            else:
                return getattr(
                    check.with_context(action_date=self.date, journal_type=journal_type, partner=self.partner_id.id), self.action_type)()
        if self.action_type == 'deposited':
            if self.check_ids:
                return getattr(
                    self.check_ids.with_context(action_date=self.date, journal_type=journal_type, journal=self.journal_id.id, default_communication=self.communication), self.action_type)()
            else:
                return getattr(
                    check.with_context(action_date=self.date, journal_type=journal_type, journal=self.journal_id.id, default_communication=self.communication), self.action_type)()

        if self.action_type in ['bank_debit', 'reject_holding']:
            if self.check_ids:
                return getattr(
                    self.check_ids.with_context(action_date=self.date), self.action_type)()
            else:
                return getattr(
                    check.with_context(action_date=self.date), self.action_type)()

        if self.partner_id:
            return getattr(
                check.with_context(action_date=self.date, partner=self.partner_id.id), self.action_type)()
        else:
            return getattr(
                check.with_context(action_date=self.date), self.action_type)()

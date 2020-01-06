# -*- coding: utf-8 -*-

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)



class AccountCheck(models.Model):

    _name = 'account.check'
    _description = 'Account Check'
    _order = "id desc"
    _inherit = ['mail.thread']

    def _domain_journal_id(self):
        domain = [('type', 'in', ['cash', 'bank'])]
        if self._context.get('default_type'):
            if self._context['default_type'] == 'third_check':
                payment_method_id = self.env.ref(
                    'l10n_ar_account_check.account_payment_method_received_third_check')
                journal_ids = self.env['account.journal'].search(domain).filtered(
                    lambda x: payment_method_id in x.inbound_payment_method_ids).ids
            else:
                payment_method_id = self.env.ref('l10n_ar_account_check.account_payment_method_own_check')
                journal_ids = self.env['account.journal'].search(domain).filtered(
                    lambda x: payment_method_id in x.outbound_payment_method_ids).ids
            domain = [('id', 'in', journal_ids)]
        return domain

    name = fields.Char(string="Name", readonly=True, copy=False, states={'draft': [('readonly', False)]})
    number = fields.Integer(string="Number", required=True, readonly=True, copy=False, states={'draft': [('readonly', False)]})
    checkbook_id = fields.Many2one('account.checkbook', string='Checkbook', readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
                                 domain=lambda self: self._domain_journal_id(), readonly=True,
                                 states={'draft': [('readonly', False)]})
    type = fields.Selection([('own_check', 'Own Check'),
                             ('third_check', 'Third Check')], string="Type", readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    operation_partner_id = fields.Many2one(
        'res.partner',
        string='Operation Partner',
        compute='_compute_operation_partner_id'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('use', 'In use'),
        ('negotiated', 'Negotiated'),
        ('handed', 'Handed'),
        ('selled', 'Selled'),
        ('debited', 'Debited'),
        ('rejected', 'Rejected'),
        ('holding', 'Holding'),
        ('deposited', 'Deposited'),
        ('delivered', 'Delivered'),
        ('transfered', 'Transfered'),
        ('reclaimed', 'Reclaimed'),
        # ('withdrawed', 'Withdrawed'),
        ('returned', 'Returned'),
        ('changed', 'Changed'),
        ('cancel', 'Cancel'),
    ], required=True, default='draft', copy=False, compute='_compute_state', store=True)
    emission_date = fields.Date(string='Emission Date', required=True, readonly=True,
                                states={'draft': [('readonly', False)]}, default=fields.Date.context_today)
    payment_date = fields.Date(readonly=True, states={'draft': [('readonly', False)]})
    deposited_date = fields.Date(string='Deposited date')
    deposited_journal_id = fields.Many2one('account.journal', string='Deposited Journal')
    deposited_bank_id = fields.Many2one('res.bank', string='Deposited Bank')
    owner_cuit = fields.Char(string='Owner CUIT', readonly=True, states={'draft': [('readonly', False)]})
    owner_name = fields.Char(string='Owner Name', readonly=True, states={'draft': [('readonly', False)]})
    owner_vat = fields.Char('Owner Vat', readonly=True, states={'draft': [('readonly', False)]})
    bank_id = fields.Many2one('res.bank', string='Bank', readonly=True, states={'draft': [('readonly', False)]})

    amount = fields.Monetary(currency_field='company_currency_id', readonly=True, states={'draft': [('readonly', False)]})
    amount_currency = fields.Monetary(currency_field='currency_id', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', readonly=True, states={'draft': [('readonly', False)]})

    company_id = fields.Many2one(related='journal_id.company_id', readonly=True, store=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    operation_ids = fields.One2many('account.check.operation', 'check_id')
    note = fields.Char(string='Nota')
    operation_no = fields.Char(string='Operation No.')
    own_check_subtype = fields.Selection(related='checkbook_id.own_check_subtype')
    payment_method_id = fields.Many2one('account.payment.method', compute='_compute_payment_method_id', store=True, copy=False)

    move_id = fields.Many2one('account.move', string='Move', index=True)
    transfer_journal_id = fields.Many2one('account.journal', string='Deposited Journal',
                                          compute='_compute_transfer_journal_id', store=True, copy=False)
    lot_sale = fields.Char(string='Lot of sale', readonly=True, states={'negotiated': [('readonly', False)]})

    @api.multi
    @api.depends('operation_ids')
    def _compute_state(self):
        for rec in self:
            if rec.operation_ids:
                rec.state = rec.operation_ids.filtered(lambda x: x.operation != 'transfered')[0].operation
            else:
                rec.state = 'draft'

    @api.multi
    @api.depends('operation_ids', 'state')
    def _compute_operation_partner_id(self):
        for rec in self:
            operations = rec.operation_ids.filtered(lambda x: x.operation == rec.state)
            if rec.state == 'holding':
                rec.operation_partner_id = rec.company_id.partner_id.id
            elif operations:
                rec.operation_partner_id = operations[0].partner_id.id
            else:
                rec.operation_partner_id = False

    # ~ @api.one
    @api.onchange('journal_id')
    def onchange_journal_id(self):
        if self.type == 'own_check':
            self.bank_id = self.journal_id.bank_id
            return {'domain': {'bank_id': [('id', '=', self.journal_id.bank_id.id)]}}

    @api.onchange('partner_id')
    def onchange_partner_check(self):
        commercial_partner = self.partner_id.commercial_partner_id
        if self.type == 'third_check':
            self.owner_name = commercial_partner.name
            vat_field = 'vat'
            if 'cuit' in commercial_partner._fields:
                vat_field = 'cuit'
            self.owner_vat = commercial_partner[vat_field]

    @api.multi
    @api.depends('type')
    def _compute_payment_method_id(self):
        for rec in self:
            if rec.type == 'third_check':
                rec.payment_method_id = self.env.ref('l10n_ar_account_check.account_payment_method_received_third_check').id
            else:
                rec.payment_method_id = self.env.ref('l10n_ar_account_check.account_payment_method_own_check').id

    @api.multi
    @api.depends('deposited_journal_id', 'journal_id')
    def _compute_transfer_journal_id(self):
        for rec in self:
            if rec.type == 'third_check' and rec.state == 'deposited':
                rec.transfer_journal_id = rec.deposited_journal_id.id
            else:
                rec.transfer_journal_id = rec.journal_id.id

    @api.multi
    @api.depends('name', 'bank_id', 'owner_name')
    def get_check_name(self):
        for record in self:
            name = record.name or ''
            if not record.name:
                name = record.number and str(record.number) or ''
            if record.bank_id:
                name += ' / ' + record.bank_id.name
            if record.owner_name:
                name += ' / ' + record.owner_name
            record.check_name = name

    check_name = fields.Char(string='Check Name', compute=get_check_name)

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = record.name or ''
            if not record.name:
                name = record.number and str(record.number) or ''
            if record.bank_id:
                name += ' / ' + record.bank_id.name
            if record.owner_name:
                name += ' / ' + record.owner_name
            result.append((record.id, name))
        return result

    @api.multi
    def _update_check_cancel(self, payment):
        for rec in self:
            if rec.state in ['holding'] and rec.type == 'third_check' and payment.payment_type in ['inbound', 'transfer']:
                operation = rec._get_init_operation('holding', True)
                if operation and operation.origin and operation.origin._name == 'account.payment':
                    rec._create_operation('cancel', payment, operation.partner_id, date=operation.date)

                if payment.payment_method_code == 'delivered_third_check' and payment.payment_type == 'transfer':
                    inbound_method = (payment.destination_journal_id.inbound_payment_method_ids)
                    if len(inbound_method) == 1 and (
                            inbound_method.code == 'received_third_check'):
                        rec.journal_id = operation.origin.journal_id.id

            elif rec.state in ['delivered'] and rec.type == 'third_check' and payment.payment_type == 'outbound':
                operation = rec._get_operation('delivered', True)
                if operation and operation.origin and operation.origin._name == 'account.payment':
                    rec._create_operation('holding', payment, operation.partner_id, date=operation.date)

            elif rec.state in ['handed'] and rec.type == 'own_check':
                operation = rec._get_operation('handed', True)
                if operation and operation.origin and operation.origin._name == 'account.payment':
                    rec._create_operation('draft', payment, operation.partner_id, date=operation.date)

            elif rec.state in ['transfered'] and payment.payment_type == 'transfer':
                operation = self.operation_ids.search([('check_id', '=', self.id)], limit=2)
                if operation and operation[0].origin and operation[0].origin._name == 'account.payment':
                    rec._create_operation(operation[1].operation, operation[1].origin, operation.partner_id, date=operation.date)
            else:
                raise UserError(
                    _('You cannot cancel a payment with a %s check because you are in another state unrelated to the payment, this check operation must be changed.')% rec.number)

    def _get_init_operation(self, operation, partner_required=False):
        self.ensure_one()
        op = self.operation_ids.search([
            ('check_id', '=', self.id), ('operation', '=', operation)], order='date,id asc',
            limit=1)
        if partner_required:
            if not op.partner_id:
                raise ValidationError((
                    'The %s (id %s) operation has no partner linked.'
                    'You will need to do it manually.') % (operation, op.id))
        return op

    @api.multi
    def _create_operation(self, operation, origin, partner=None, date=False):
        for rec in self:
            date = date or fields.Date.today()
            if rec.operation_ids and rec.operation_ids[0].date > date:
                raise ValidationError(_(
                    'The date of a new check operation can not be minor than '
                    'last operation date'))
            origin_ref = False
            origin_name = _('Beginning balance')
            if origin:
                id, origin_name = origin.name_get()[0]
                origin_ref = '%s,%i' % (origin._name, origin.id)
            elif operation == 'negotiated':
                origin_name = _('Negotiation of sale check')
            elif operation == 'draft':
                origin_name = _('Draft Check')
            elif operation == 'rejected':
                origin_name = _('Reject')
            vals = {
                'operation': operation,
                'date': date,
                'check_id': rec.id,
                'origin_name': origin_name,
                'origin': origin_ref,
                'partner_id': partner and partner.id or False,
            }
            rec.operation_ids.create(vals)

    @api.multi
    def _get_operation(self, operation, partner_required=False):
        self.ensure_one()
        op = self.operation_ids.search([
            ('check_id', '=', self.id), ('operation', '=', operation)],
            limit=1)
        if partner_required:
            if not op.partner_id:
                raise ValidationError((
                      'The %s (id %s) operation has no partner linked.'
                      'You will need to do it manually.') % (operation, op.id))
        return op

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise ValidationError(
                    _('The Check must be in draft state for unlink !'))
        return super(AccountCheck, self).unlink()

    def _get_name_from_number(self, number):
        padding = 8
        if len(str(number)) > padding:
            padding = len(str(number))
        return ('%%0%sd' % padding % number)

    @api.model
    def create(self, vals):
        checkbook = self.env['account.checkbook']
        if self._context.get('default_type') and self._context.get('default_type') == 'own_check':
            checkbook_id = checkbook.browse(vals.get('checkbook_id'))
            if checkbook_id.own_check_subtype != 'electronic':
                vals['number'] = checkbook_id.next_number
                checkbook_id.update_next_number()
                vals['name'] = self._get_name_from_number(vals['number'])
        if not vals.get('name', False):
            vals['name'] = self._get_name_from_number(vals['number'])
        rec = super(AccountCheck, self).create(vals)
        return rec

    @api.multi
    def bank_debit(self):
        for rec in self:
            if rec.state in ['handed', 'selled'] and rec.type == 'own_check':
                if rec.state == 'selled':
                    vals = rec.get_bank_vals(
                        'bank_debit_selled', rec.journal_id)
                else:
                    vals = rec.get_bank_vals(
                    'bank_debit', rec.journal_id)
                action_date = self._context.get('action_date')
                vals['date'] = action_date
                move = self.env['account.move'].create(vals)
                rec.handed_reconcile(move)
                move.post()
                rec._create_operation('debited', move, date=action_date)

    @api.multi
    def get_bank_vals(self, action, journal):
        self.ensure_one()
        if action == 'bank_debit':
            credit_account = journal.default_debit_account_id
            debit_account = self.company_id._get_check_account('deferred')
            name = _('Check "%s" debit') % (self.name)
        elif action == 'bank_debit_selled':
            credit_account = journal.default_debit_account_id
            debit_account = self.company_id._get_check_account('selled')
            name = _('Check "%s" debit') % (self.name)
        elif action == 'bank_reject':
            credit_account = journal.default_debit_account_id
            debit_account = self.company_id._get_check_account('rejected')
            name = _('Check "%s" rejection') % (self.name)
        else:
            raise ValidationError(_(
                'Action %s not implemented for checks!') % action)
        debit_line_vals = {
            'name': name,
            'account_id': debit_account.id,
            'debit': self.amount,
            'amount_currency': self.amount_currency,
            'currency_id': self.currency_id.id,
        }
        credit_line_vals = {
            'name': name,
            'account_id': credit_account.id,
            'credit': self.amount,
            'amount_currency': self.amount_currency,
            'currency_id': self.currency_id.id,
        }
        return {
            'ref': name,
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'line_ids': [
                (0, False, debit_line_vals),
                (0, False, credit_line_vals)],
        }

    @api.multi
    def use(self):
        self.ensure_one()
        self.check_data()
        self.check_use_data()
        if not self.partner_id:
            self.partner_id = self.company_id.partner_id
        view_id = self.env.ref('account.view_move_form').id
        if self.state in ['draft']:
            name = _('Check "%s" use') % (self.name)
            vals = self.get_use_vals(self.journal_id)
            #move = self.env['account.move'].new(vals)
            #self.move_id = move
            #self.handed_reconcile(move)
            #move.post()
            #self._create_operation('use', move, date=action_date)
            action_context = vals
            return {
                'name': name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.move',
                'view_id': view_id,
                'type': 'ir.actions.act_window',
                'context': action_context,
            }

    def check_data(self):
        for rec in self:
            payment = self.env['account.payment'].search([('check_id', '=', rec.id)])
            if payment:
                raise ValidationError(_(
                    'To use the check can not be selected in any payment'))
            if not rec.amount > 0.0:
                raise ValidationError(_(
                    'The amount of the check must be greater than zero'))
            if not rec.payment_date:
                raise ValidationError(_(
                    'You must complete the payment date'))

    def check_use_data(self):
        #if self.partner_id and self.partner_id != self.company_id.partner_id:
        if not self.partner_id:
            raise ValidationError(_(
                'The check must be issued in the name of a partner'))

    @api.multi
    def get_use_vals(self, journal):
        self.ensure_one()
        credit_account = journal.default_debit_account_id
        name = _('Check "%s" use') % (self.name)
        credit_line_vals = {
            'name': name,
            'account_id': credit_account.id,
            'debit': 0.0,
            'credit': self.amount,
            'journal_id': journal.id,
            'analytic_tag_ids': []
        }
        return {
            'default_ref': name,
            'default_journal_id': journal.id,
            'default_date': self._context.get('action_date'),
            'default_check_id': self.id,
            'default_check_operation': 'use',
            'default_line_ids': [(0, 0, credit_line_vals)]
        }

    @api.multi
    def handed_reconcile(self, move):

        self.ensure_one()
        if self.state == 'selled':
            debit_account = self.company_id._get_check_account('selled')
            operation = self._get_operation('selled')
        else:
            debit_account = self.company_id._get_check_account('deferred')
            operation = self._get_operation('handed')

        # conciliamos
        if debit_account.reconcile:
            if operation.origin:
                if operation.origin._name == 'account.payment':
                    move_lines = operation.origin.move_line_ids
                elif operation.origin._name == 'account.move':
                    move_lines = operation.origin.line_ids
                move_lines |= move.line_ids
                move_lines = move_lines.filtered(
                    lambda x: x.account_id == debit_account)
                if len(move_lines) != 2:
                    raise ValidationError((
                                              'Se encontraron mas o menos que dos apuntes contables '
                                              'para conciliar en el débito del cheque.\n'
                                              '*Apuntes contables: %s') % move_lines.ids)
                move_lines.reconcile()

    @api.multi
    def negotiated(self):
        if self[0].type == 'third_check':
            check = self.filtered(lambda x: x.state not in ['holding'])
            if check:
                raise ValidationError(('You can only negotiate checks that are in hand.'))
        else:
            check = self.filtered(lambda x: x.state not in ['draft'])
            if check:
                raise ValidationError(('You can only negotiate checks that are in draft.'))
        self.check_data()
        action_date = self._context.get('action_date')
        for rec in self:
            if not rec.partner_id:
                rec.partner_id = rec.company_id.partner_id
        if self._context.get('partner'):
            partner = self.env['res.partner'].browse(self._context.get('partner'))
        else:
            partner = False
        self._create_operation('negotiated', False, partner, date=action_date)

    @api.multi
    def selled(self):
        self.check_seller()
        action_date = self._context.get('action_date')
        if self._context.get('partner'):
            partner = self.env['res.partner'].browse(self._context.get('partner'))
        else:
            partner = False
        if self._context.get('journal'):
            journal = self.env['account.journal'].browse(self._context.get('journal'))
        else:
            journal = False
        if self._context.get('expense_account'):
            expense_account = self.env['account.account'].browse(self._context.get('expense_account'))
        else:
            expense_account = False
        debit_note = self._context.get('debit_note', False)
        expense_amount = self._context.get('expense_amount', 0.0)
        lot_sale = self.env['ir.sequence'].with_context(ir_sequence_date=action_date).next_by_code(
                'sequence.selled.check')
        self.write({
            'lot_sale': lot_sale
        })
        if journal and expense_account:
            amount_total = sum(x.amount for x in self)
            vals = self[0].get_move_vals(
                    debit_note, journal, expense_account, expense_amount, amount_total)

            action_date = self._context.get('action_date')
            vals['date'] = action_date
            move = self.env['account.move'].create(vals)
            move.post()
            self._create_operation('selled', move, partner, date=action_date)
            if debit_note and expense_amount > 0.0:
                tax_ids = self._context.get('tax_ids')
                return self[0].action_create_debit_note('selled', 'supplier', partner,
                    expense_account, expense_amount, tax_ids)

    @api.multi
    def deposited(self):
        action_date = self._context.get('action_date')
        self.check_deposited(action_date)
        if self._context.get('journal'):
            journal = self.env['account.journal'].browse(self._context.get('journal'))
        else:
            journal = False
        if journal:
            if self[0].type == 'own_check':
                check_journal = self.filtered(lambda x: x.journal_id == journal)
                if check_journal:
                    raise ValidationError((
                        'You should not deposit a check in the same bank where it was generated.'))
            amount_total = sum(x.amount for x in self)
            vals = self[0].get_payment_vals(journal, amount_total, action_date)
            ctx = dict(self._context)
            if self[0].type == 'own_check':
                vals['check_own_ids'] = [(4, check.id, None) for check in self]
                if ctx.get('default_check_ids', False):
                    ctx['default_check_ids'] = False
            else:
                vals['check_ids'] = [(4, check.id, None) for check in self]
            payment = self.env['account.payment'].with_context(ctx).create(vals)
            payment.post()
            view_id = self.env.ref('account_payment_group.view_account_payment_transfer_form').id
            return {
                'name': _('Deposited Checks'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.payment',
                'view_id': view_id,
                'res_id': payment.id,
            }

    @api.multi
    def get_move_vals(self, debit_note, journal, expense_account, expense_amount, amount_total=0.0):
        self.ensure_one()
        if self.type == 'third_check':
            credit_account = self.journal_id.default_credit_account_id
        else:
            credit_account = self.company_id._get_check_account('selled')
        debit_account = journal.default_debit_account_id
        name = _('Lot check "%s" sold') % (self.lot_sale)
        debit = self.amount if amount_total == 0.0 else amount_total
        amount_move = self.amount if amount_total == 0.0 else amount_total
        line_ids = []
        debit_line_vals1 = False
        if not debit_note:
            debit = amount_move - expense_amount
            debit_line_vals1 = {
                'name': name,
                'account_id': expense_account.id,
                'debit': expense_amount,
                'amount_currency': self.amount_currency,
                'currency_id': self.currency_id.id,
            }
        debit_line_vals = {
            'name': name,
            'account_id': debit_account.id,
            'debit': debit,
            'amount_currency': self.amount_currency,
            'currency_id': self.currency_id.id,
        }
        line_ids.append((0, False, debit_line_vals))
        if debit_line_vals1:
            line_ids.append((0, False, debit_line_vals1))
        credit_line_vals = {
            'name': name,
            'account_id': credit_account.id,
            'credit': amount_move,
            'amount_currency': self.amount_currency,
            'currency_id': self.currency_id.id,
        }
        line_ids.append((0, False, credit_line_vals))
        return {
            'ref': name,
            'journal_id': journal.id,
            'check_id': self.id,
            'check_operation': 'selled',
            'date': fields.Date.today(),
            'line_ids': line_ids,
        }

    @api.multi
    def get_payment_vals(self, journal, amount_total=0.0, date=False):
        self.ensure_one()
        if self[0].type == 'third_check':
            payment_method = self.env.ref('l10n_ar_account_check.account_payment_method_delivered_third_check', False)
        else:
            payment_method = self.env.ref('l10n_ar_account_check.account_payment_method_own_check', False)
        return {
            'journal_id': self[0].journal_id.id,
            'destination_journal_id': journal.id,
            'amount':  amount_total,
            'payment_date': date and date or fields.Date.today(),
            'payment_method_id': payment_method and payment_method.id or False,
            'payment_type': 'transfer',
        }

    @api.multi
    def reject(self):
        self.ensure_one()
        if self.state == 'handed':
            operation = self._get_operation(self.state, True)
            return self.action_create_debit_note(
                'rejected', 'supplier', operation.partner_id,
                self.company_id._get_check_account('deferred'))
        elif self.state == 'delivered':
            operation = self._get_operation(self.state, True)
            return self.action_create_debit_note(
                'rejected', 'supplier', operation.partner_id,
                self.company_id._get_check_account('rejected'))
        elif self.state in ['deposited', 'changed']:
            if self.type == 'third_check':
                operation = self._get_operation(self.state)
                if operation.origin._name == 'account.payment':
                    journal = operation.origin.destination_journal_id
                # for compatibility with migration from v8
                elif operation.origin._name == 'account.move':
                    journal = operation.origin.journal_id
                else:
                    raise ValidationError((
                        'The deposit operation is not linked to a payment.'
                        'If you want to reject you need to do it manually.'))
                vals = self.get_bank_vals(
                    'bank_reject', journal)
                action_date = self._context.get('action_date')
                vals['date'] = action_date
                move = self.env['account.move'].create(vals)
                move.post()
                self._create_operation('rejected', move, date=action_date)
            else:
                operation = self._get_operation(self.state)
                if operation.origin._name == 'account.payment':
                    move_account_line = operation.origin.move_line_ids
                    move_account_line.remove_move_reconcile()
                    operation.origin.cancel()
                elif operation.origin._name == 'account.move':
                    # journal = operation.origin.journal_id
                    operation.origin.reverse_moves()
                else:
                    raise ValidationError((
                        'The deposit operation is not linked to a payment.'
                        'If you want to reject you need to do it manually.'))
                action_date = self._context.get('action_date')
                self._create_operation('rejected', False, date=action_date)

    @api.multi
    def reject_holding(self):
        for rec in self:
            if rec.state in ['deposited', 'changed']:
                operation = rec._get_operation(rec.state)
                if operation.origin._name == 'account.payment':
                    move_account_line = operation.origin.move_line_ids
                    move_account_line.remove_move_reconcile()
                    operation.origin.cancel()
                    #journal = operation.origin.destination_journal_id
                # for compatibility with migration from v8
                elif operation.origin._name == 'account.move':
                    #journal = operation.origin.journal_id
                    operation.origin.reverse_moves()
                else:
                    raise ValidationError((
                        'The deposit operation is not linked to a payment.'
                        'If you want to reject you need to do it manually.'))
                if rec.state == 'deposited':
                    rec.deposited_date = False
                    rec.deposited_journal_id = self.env['account.journal']
                    rec.deposited_bank_id = self.env['res.bank']
                if rec.type == 'own_check':
                    action_date = self._context.get('action_date')
                    rec._create_operation('draft', False, date=action_date)
                else:
                    action_date = self._context.get('action_date')
                    operation_holding = rec._get_operation('holding')
                    rec._create_operation('holding', operation_holding.origin, date=action_date)


    @api.multi
    def action_draft(self):
        self.ensure_one()
        if self.state in ['use', 'negotiated', 'holding']:
            self.partner_id = self.env['res.partner']
            if self.state == 'use':
                operation = self._get_operation(self.state)
                if operation.origin._name == 'account.move':
                    move = operation.origin
                    reverse_move = move.reverse_moves(date=move.date)
                    origin = reverse_move[0] if reverse_move else move
                    if origin:
                        origin = self.env['account.move'].browse(origin)
                    self._create_operation('draft', origin)
                    if self.move_id:
                        self.move_id = self.env['account.move']
            elif self.state == 'holding':
                operation = self._get_operation(self.state)
                if operation.origin and operation.origin._name == 'account.payment':
                    raise ValidationError(_(
                        'You can not reprint a third party check generated by a bill.'))
                else:
                    self._create_operation('draft', False)
            else:
                self._create_operation('draft', False)

    @api.multi
    def action_cancel(self):
        self.ensure_one()
        if self.state == 'returned':
            self.state = 'cancel'

    @api.multi
    def action_holding(self):
        self.ensure_one()
        if self.state == 'draft' or self.state == 'cancel':
            self.state = 'holding'
            self._create_operation(
                self.state, False, self.partner_id)

    @api.multi
    def action_create_debit_note(
            self, operation, partner_type, partner, account, amount=0.0, tax_ids=False):
        self.ensure_one()
        action_date = self._context.get('action_date')

        if partner_type == 'supplier':
            invoice_type = 'in_refund'
            refund_type = 'debit'
            journal_type = 'purchase'
            view_id = self.env.ref('account.invoice_supplier_form').id
        else:
            invoice_type = 'out_refund'
            journal_type = 'sale'
            refund_type = 'debit'
            view_id = self.env.ref('account.invoice_form').id

        tipo_comprobante = self.get_tipo_comprobante(partner)

        journal = False
        if tipo_comprobante:
            journal = self.get_journal(tipo_comprobante, invoice_type)
        if not journal:
            journal = self.env['account.journal'].search([
                ('company_id', '=', self.company_id.id),
                ('type', '=', journal_type),
            ], limit=1)

        if operation in ['rejected', 'reclaimed']:
            name = 'Rechazo cheque "%s"' % (self.check_name)
        elif operation in ['selled']:
            name = 'Venta de lote de cheques "%s"' % (self.lot_sale)
        elif operation == 'returned':
            name = 'Devolucion cheque "%s"' % (self.check_name)
        else:
            raise ValidationError(_(
                'Debit note for operation %s not implemented!' % (
                    operation)))
        if amount > 0.0:
            price_unit = amount
        else:
            price_unit = (self.amount_currency and self.amount_currency or self.amount)

        inv_line_vals = {
            'name': name,
            'account_id': account.id,
            'price_unit': price_unit,
        }
        if tax_ids:
            inv_line_vals['invoice_line_tax_ids'] = [(6, 0, tax_ids)]

        inv_vals = {
            'rejected_check_id': self.id,
            'reference': name,
            'date_invoice': action_date,
            'origin': _('Check nbr (id): %s (%s)') % (self.check_name, self.id),
            'journal_id': journal.id,
            'tipo_comprobante': tipo_comprobante.id if tipo_comprobante else False,
            'refund_type': refund_type,
            'partner_id': partner.id,
            'type': invoice_type,
            'invoice_line_ids': [(0, 0, inv_line_vals)],
        }
        inv_vals = self.update_invoice_value(inv_vals)
        if self.currency_id:
            inv_vals['currency_id'] = self.currency_id.id
        invoice = self.env['account.invoice'].with_context(
            internal_type='debit_note', journal_type=journal_type).create(inv_vals)
        if operation != 'selled':
            self._create_operation(operation, invoice, partner, date=action_date)

        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'view_id': view_id,
            'res_id': invoice.id,
            'type': 'ir.actions.act_window',
        }

    def update_invoice_value(self, inv_vals):
        inv_vals.update({'not_commission': True,})
        return inv_vals

    def get_tipo_comprobante(self, partner):
        refund_comp = self.env['tipo.comprobante']
        if partner and partner.responsability_id and partner.responsability_id.comprobante_default:
            refund_comp = self.env['tipo.comprobante'].search([
                ('referencia_id', '=', partner.responsability_id.comprobante_default.id),
                ('type', '=', 'debit_note')
            ], limit=1)
        return refund_comp

    def get_journal(self, tipo_comprobante, invoice_type):
        type_clause = invoice_type in ['out_invoice', 'out_refund'] and ('type', '=', 'sale') or (
        'type', '=', 'purchase')
        journal = self.env['account.journal'].search([
            ('comprobante_id', '=', tipo_comprobante.id),
            ('company_id', '=', self.env.user.company_id.id),
            type_clause
        ])
        return journal and journal or False

    @api.model
    def get_third_check_account(self):
        account = self.env['account.account']
        for rec in self:
            credit_account = rec.journal_id.default_credit_account_id
            debit_account = rec.journal_id.default_debit_account_id
            inbound_methods = rec.journal_id['inbound_payment_method_ids']
            outbound_methods = rec.journal_id['outbound_payment_method_ids']
            if credit_account and credit_account == debit_account and len(
                    inbound_methods) == 1 and len(outbound_methods) == 1:
                account |= credit_account
            else:
                account |= rec.company_id._get_check_account('holding')
        if len(account) != 1:
            raise ValidationError(_('Error not specified'))
        return account

    @api.multi
    def claim(self):
        self.ensure_one()
        if self.state in ['rejected'] and self.type == 'third_check':
            # anulamos la operación en la que lo recibimos
            operation = self._get_operation('holding', True)
            return self.action_create_debit_note(
                'reclaimed', 'customer', self.partner_id,
                self.company_id._get_check_account('rejected'))

    @api.multi
    def customer_return(self):
        self.ensure_one()
        if self.state in ['holding'] and self.type == 'third_check':
            operation = self._get_operation('holding', True)
            return self.action_create_debit_note(
                'returned', 'customer', operation.partner_id,
                self.get_third_check_account())

    @api.multi
    def check_seller(self):
        operation_partner = self.mapped('operation_partner_id')
        if len(operation_partner) != 1:
            raise ValidationError(_(
                'You can not sell checks that have been negotiated with different contacts.'))
        check = self.filtered(lambda x: x.state != 'negotiated')
        if check:
            raise ValidationError(_(
                'You can only sell checks that have not been negotiated.'))
        return True

    @api.multi
    def check_deposited(self, date):
        if self[0].type == 'third_check':
            check = self.filtered(lambda x: x.state != 'holding')
            if check:
                raise ValidationError((
                    'You can only deposited checks that have not been holding.'))
        else:
            check = self.filtered(lambda x: x.state != 'draft')
            if check:
                raise ValidationError((
                    'You can only deposited checks that have not been draft.'))
        if self.filtered(lambda x: not x.payment_date):
            raise ValidationError((
                'You must specify the check payment date.'))
        check_date = self.filtered(lambda x: x.payment_date > date)
        if check_date:
            raise ValidationError((
                'You can only deposit a check that the deposit date is less than the date of the operation.'))
        return True


class AccountCheckOperation(models.Model):

    _name = 'account.check.operation'
    _rec_name = 'operation'
    _order = 'id desc'

    date = fields.Date(default=fields.Date.context_today,)
    check_id = fields.Many2one(
        'account.check',
        'Check',
        required=True,
        ondelete='cascade',
        auto_join=True,
    )
    operation = fields.Selection([
        ('draft', 'Draft'),
        ('use', 'In use'),
        ('negotiated', 'Negotiated'),
        ('handed', 'Handed'),
        ('selled', 'Selled'),
        ('debited', 'Debited'),
        ('rejected', 'Rejected'),
        ('holding', 'Holding'),
        ('deposited', 'Deposited'),
        ('delivered', 'Delivered'),
        ('transfered', 'Transfered'),
        ('reclaimed', 'Reclaimed'),
        #('withdrawed', 'Withdrawed'),
        ('returned', 'Returned'),
        ('changed', 'Changed'),
        ('cancel', 'Cancel'),
    ],required=True)
    origin_name = fields.Char(string='Origin name',  required=True)
    origin = fields.Reference(string='Origin Document', selection='_reference_models')
    partner_id = fields.Many2one('res.partner', string='Partner')
    notes = fields.Text(string='Note')

    @api.model
    def _reference_models(self):
        return [
            ('account.payment', 'Payment'),
            ('account.check', 'Check'),
            ('account.invoice', 'Invoice'),
            ('account.move', 'Journal Entry')
        ]




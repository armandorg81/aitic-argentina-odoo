# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)



class AccountPayment(models.Model):

    _inherit = 'account.payment'

    check_ids = fields.Many2many(
        'account.check',
        string='Checks',
        copy=False
    )
    check_own_ids = fields.Many2many(
        'account.check',
        string='Checks Own',
        copy=False
    )
    transfer_check_ids = fields.Many2many(
        'account.check',
        string='Checks Transfer',
        copy=False
    )
    #check_ids_copy = fields.Many2many(
        #related='check_ids',
        #readonly=True,
    #)
    readonly_currency_id = fields.Many2one(
        related='currency_id',
        readonly=True,
    )
    readonly_amount = fields.Monetary(
        related='amount',
        readonly=True,
    )
    check_id = fields.Many2one(
        'account.check',
        #compute='_compute_check',
        string='Check',
        copy=False,
    )

    @api.multi
    @api.depends('check_ids', 'transfer_check_ids', 'check_own_ids')
    def _compute_check(self):
        for rec in self:
            if rec.payment_method_code in ('own_check') and rec.payment_type == 'transfer' and len(rec.check_ids) == 1:
                rec.check_id = rec.check_own_ids[0].id
            elif rec.payment_method_code in (
                    'received_third_check',
                    'own_check',) and len(rec.check_ids) == 1:
                rec.check_id = rec.check_ids[0].id
            elif rec.payment_method_code in (
                    'transfer_check') and len(rec.transfer_check_ids) == 1:
                rec.check_id = rec.transfer_check_ids[0].id

    check_name = fields.Char(
        'Check Name',
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]},
        default= "00000000"
    )
    check_number = fields.Integer(
        'Check Number',
        readonly=True,
        copy=False
    )
    check_own_date = fields.Date(
        'Check own Date',
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]},
        default=fields.Date.context_today,
    )
    check_payment_date = fields.Date(
        'Check Payment Date',
        readonly=True,
        help="Only if this check is post dated",
        states={'draft': [('readonly', False)]}
    )
    checkbook_id = fields.Many2one(
        'account.checkbook',
        'Checkbook',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    check_subtype = fields.Selection(
        related='checkbook_id.own_check_subtype',
        readonly=True,
    )
    check_bank_id = fields.Many2one(
        'res.bank',
        'Check Bank',
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]}
    )
    check_owner_vat = fields.Char(
        'Check Owner Vat',
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]}
    )
    check_owner_name = fields.Char(
        'Check Owner Name',
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]}
    )
    check_type = fields.Char(
        compute='_compute_check_type',
    )
    checkbook_block_manual_number = fields.Boolean(
        related='checkbook_id.block_manual_number',
    )
    #check_number_readonly = fields.Integer(
        #related='check_number',
        #readonly=True,
    #)
    operation_no = fields.Char(string='Operation No.')

    @api.multi
    @api.depends('payment_method_code')
    def _compute_check_type(self):
        for rec in self:
            if rec.payment_method_code == 'own_check':
                rec.check_type = 'own_check'
            elif rec.payment_method_code == 'received_third_check' or rec.payment_method_code == 'delivered_third_check':
                rec.check_type = 'third_check'
            elif rec.payment_method_code == 'transfer_check':
                rec.check_type = rec.transfer_check_ids[0].type if rec.transfer_check_ids else False

    @api.onchange('journal_id')
    def _onchange_journal(self):
        res = super(AccountPayment, self)._onchange_journal()
        res['value'] = {'check_ids': []}
        res['value'] = {'transfer_check_ids': []}
        res['value'] = {'check_own_ids': []}
        return res

    @api.onchange('check_ids', 'payment_method_code')
    def onchange_checks(self):
        if self.payment_method_code == 'delivered_third_check':
            self.amount = sum(self.check_ids.mapped('amount'))

    @api.onchange('check_own_ids', 'payment_method_code')
    def onchange_own_checks(self):
        if self.payment_method_code == 'own_check' and self.payment_type == 'transfer':
            self.amount = sum(self.check_own_ids.mapped('amount'))

    @api.onchange('transfer_check_ids', 'payment_method_code')
    def onchange_transfer_checks(self):
        if self.payment_method_code == 'transfer_check':
            self.amount = sum(self.transfer_check_ids.mapped('amount'))

    @api.multi
    @api.onchange('check_number')
    def change_check_number(self):
        # TODO make default padding a parameter
        def _get_name_from_number(number):
            padding = 8
            if len(str(number)) > padding:
                padding = len(str(number))
            return ('%%0%sd' % padding % number)

        for rec in self:
            if rec.payment_method_code in ['received_third_check'] or rec.checkbook_id and rec.checkbook_id.own_check_subtype == 'electronic':
                if not rec.check_number:
                    check_name = False
                else:
                    check_name = _get_name_from_number(rec.check_number)
                rec.check_name = check_name

    @api.onchange('check_own_date', 'check_payment_date')
    def onchange_date(self):
        if (self.check_own_date and self.check_payment_date and self.check_own_date > self.check_payment_date):
            self.check_payment_date = False
            raise UserError(
                _('Check Payment Date must be greater than own Date'))

    #~ @api.one
    @api.onchange('partner_id', 'payment_method_code')
    def onchange_partner_check(self):
        commercial_partner = self.partner_id.commercial_partner_id
        if self.payment_method_code:
            if self.payment_method_code == 'received_third_check':
                self.check_bank_id = (
                    commercial_partner.bank_ids and
                    commercial_partner.bank_ids[0].bank_id or False)
                self.check_owner_name = commercial_partner.name
                vat_field = 'vat'
                if 'cuit' in commercial_partner._fields:
                    vat_field = 'cuit'
                self.check_owner_vat = commercial_partner[vat_field]
            elif self.payment_method_code == 'own_check':
                self.check_bank_id = self.journal_id.bank_id
                self.check_owner_name = False
                self.check_owner_vat = False

    #~ @api.one
    @api.onchange('check_id')
    def onchange_check(self):
        if self.check_id:
            if self.payment_method_code == 'own_check':
                self.check_name = self.check_id.name
                self.check_number = self.check_id.number
                self.check_own_date = self.check_id.emission_date
                self.check_payment_date = self.check_id.payment_date
                self.operation_no = self.check_id.operation_no
                if self.check_id.amount > 0:
                    self.amount = self.check_id.amount

    @api.onchange('payment_method_code')
    def _onchange_payment_method_code(self):
        if self.payment_method_code == 'own_check':
            checkbook = self.env['account.checkbook'].search([
                ('state', '=', 'active'),
                ('journal_id', '=', self.journal_id.id)],
                limit=1)
            self.checkbook_id = checkbook
        elif self.checkbook_id:
            # TODO ver si interesa implementar volver atras numeracion
            self.checkbook_id = False

    @api.multi
    def post(self):
        ctx = self.env.context.copy()
        ctx['enviar_post'] = True
        for rec in self:
            if rec.checkbook_id:
                rec.with_context(ctx).change_check_number()
        res = super(AccountPayment, self).post()

    @api.multi
    def cancel(self):
        for rec in self:
            if rec.state in ['confirmed', 'posted']:
                rec.do_checks_operations(cancel=True)
                rec.check_ids.write({'origin': False})
                rec.transfer_check_ids.write({'origin': False})
                rec.check_own_ids.write({'origin': False})
        res = super(AccountPayment, self).cancel()
        self.filtered(lambda x:x.check_type).write({
                                                    'check_ids': [(6, 0, [])],
                                                    'transfer_check_ids': [(6, 0, [])],
                                                    'check_own_ids': [(6, 0, [])],
                                                    'check_name': False,
                                                    'check_number': False,
                                                    'check_own_date': False,
                                                    'check_payment_date': False,
                                                    'checkbook_id': False,
                                                    'check_bank_id': False,})
        return res

    def cancel_check(self):
        for rec in self:
            if rec.state == 'cancelled':
                rec.do_checks_operations(cancel=True)
                rec.check_ids.write({'origin': False})
                rec.transfer_check_ids.write({'origin': False})
                rec.check_own_ids.write({'origin': False})
            rec.filtered(lambda x:x.check_type).write({
                                                        'check_ids': [(6, 0, [])],
                                                        'transfer_check_ids': [(6, 0, [])],
                                                        'check_own_ids': [(6, 0, [])],
                                                        'check_name': False,
                                                        'check_number': False,
                                                        'check_own_date': False,
                                                        'check_payment_date': False,
                                                        'checkbook_id': False,
                                                        'check_bank_id': False,})
    @api.multi
    def create_check(self, check_type, operation, bank):
        self.ensure_one()
        account_check_obj = self.env['account.check']
        ctx = self._context
        ch = 'register_payment' in ctx and ctx['payment_register_wzd'] or self
        check_name =  ch.check_name
        if ch.checkbook_id and ch.checkbook_id.own_check_subtype == 'electronic' and not check_name:
            check_name = ch.operation_no
        check_vals = {
            'bank_id': bank.id,
            'owner_name': ch.check_owner_name,
            'owner_vat': ch.check_owner_vat,
            'number': ch.check_number,
            'name': check_name,
            'checkbook_id': ch.checkbook_id.id,
            'emission_date': ch.check_own_date,
            'type': ch.check_type,
            'journal_id': ch.journal_id.id,
            'amount': ch.amount,
            'payment_date': ch.check_payment_date,
            'partner_id': self.partner_id.id,
            # TODO arreglar que monto va de amount y cual de amount currency
            # 'amount_currency': self.amount,
            'currency_id': ch.currency_id.id,
            'operation_no': ch.operation_no,
        }
        if ch.check_type == 'third_check':
            check_search = account_check_obj.search([
                ('bank_id', '=', bank.id),
                ('partner_id', '=', self.partner_id.id),
                ('number', '=', ch.check_number)
            ])
            if check_search:
                raise UserError(_(
                    'You can not register more than one check with the same number for the company and the registered bank.'))
        check = account_check_obj.create(check_vals)
        self.check_ids = [(4, check.id, False)]
        check._create_operation(
            operation, self, self.partner_id, date=self.payment_date)
        return check

    @api.multi
    def update_check(self, check_type, operation, check):
        self.ensure_one()
        #if ch.checkbook_id and ch.checkbook_id.own_check_subtype == 'electronic' and not check_name:
            #check_name = ch.operation_no
        check_vals = {
            #'bank_id': bank.id,
            #'owner_name': ch.check_owner_name,
            'owner_vat': self.check_owner_vat,
            #'number': ch.check_number,
            #'name': check_name,
            #'checkbook_id': ch.checkbook_id.id,
            'own_date': self.check_own_date,
            #'type': ch.check_type,
            #'journal_id': ch.journal_id.id,
            #'amount': self.amount,
            'payment_date': self.check_payment_date,
            'partner_id': self.partner_id.id,
            # TODO arreglar que monto va de amount y cual de amount currency
            # 'amount_currency': self.amount,
            'currency_id': self.currency_id.id,
            #'operation_no': ch.operation_no,
        }
        if self.amount != check.amount:
            check_vals['amount'] = self.amount
        check.write(check_vals)
        self.check_ids = [(4, check.id, False)]
        check._create_operation(
            operation, self, self.partner_id, date=self.payment_date)
        return check

    @api.multi
    def do_checks_operations(self, vals={}, cancel=False):
        self.ensure_one()
        rec = self
        if not rec.check_type:
            # continue
            return vals
        if cancel:
            rec.check_ids._update_check_cancel(rec)
            return None
        if (rec.payment_method_code == 'own_check' and rec.payment_type == 'outbound'):
            if cancel:
                return self.check_id._create_operation('draft', self, self.company_id.partner_id)
            _logger.info('Own Check')
            vals['account_id'] = self.company_id._get_check_account('deferred').id
            operation = 'handed'
            check = self.update_check(
                'own_check', operation, self.check_id)
            vals['date_maturity'] = self.check_payment_date
            vals['name'] = _('Hand check %s') % check.name
        elif (rec.payment_method_code == 'received_third_check' and rec.payment_type == 'inbound'):
            operation = 'holding'
            # if cancel:
            #     _logger.info('Cancel Receive Check')
            #     rec.check_ids._del_operation(self)
            #     rec.check_ids.unlink()
            #     return None
            _logger.info('Receive Check')
            check = self.create_check(
                'third_check', operation, self.check_bank_id)
            vals['date_maturity'] = self.check_payment_date
            vals['account_id'] = check.journal_id.default_credit_account_id.id
            vals['name'] = _('Receive check %s') % check.name
        elif (rec.payment_method_code == 'delivered_third_check' and rec.payment_type == 'outbound'):
            # if cancel:
            #     _logger.info('Cancel Deliver Check')
            #     rec.check_ids._del_operation(self)
            #     return None
            _logger.info('Deliver Check')
            rec.check_ids._create_operation(
                'delivered', rec, rec.partner_id, date=rec.payment_date)
            vals['account_id'] = rec.check_ids.get_third_check_account().id
            vals['name'] = _('Deliver checks %s') % ', '.join(
                rec.check_ids.mapped('name'))
        elif (rec.payment_method_code == 'delivered_third_check' and rec.payment_type == 'transfer'):
            if rec.destination_journal_id.type == 'cash':
                if cancel:
                    _logger.info('Cancel Change Check')
                #     rec.check_ids._del_operation(self)
                    return None

                _logger.info('Change Check')
                rec.check_ids._create_operation(
                    'changed', rec, False, date=rec.payment_date)
                vals['account_id'] = rec.check_ids.get_third_check_account().id
                vals['name'] = _('Change check %s') % ', '.join(
                    rec.check_ids.mapped('name'))
            else:
                if cancel:
                     _logger.info('Cancel Deposit Check')
                #     rec.check_ids._del_operation(self)
                     return None
                _logger.info('Deposit Check')
                rec.check_ids._create_operation(
                    'deposited', rec, False, date=rec.payment_date)
                rec.check_ids.write({
                    'deposited_journal_id': rec.destination_journal_id.id,
                    'deposited_bank_id': rec.destination_journal_id.bank_id.id,
                    'deposited_date': rec.payment_date,
                })
                vals['account_id'] = rec.check_ids.get_third_check_account().id
                vals['name'] = _('Deposit checks %s') % ', '.join(
                    rec.check_ids.mapped('name'))
        elif (rec.payment_method_code == 'own_check' and rec.payment_type == 'transfer'):
            if rec.destination_journal_id.type == 'cash':
                if cancel:
                    _logger.info('Cancel Sell Check')
                #     rec.check_ids._del_operation(self)
                    return None

                _logger.info('Change Check')
                rec.check_ids._create_operation(
                    'changed', rec, False, date=rec.payment_date)
                vals['account_id'] = rec.check_ids.get_third_check_account().id
                vals['name'] = _('Sell check %s') % ', '.join(
                    rec.check_ids.mapped('name'))
            else:
                if cancel:
                     _logger.info('Cancel Deposit Check')
                #     rec.check_ids._del_operation(self)
                     return None
                _logger.info('Deposit Check')
                rec.check_ids._create_operation(
                    'deposited', rec, False, date=rec.payment_date)
                rec.check_ids.write({
                    'deposited_journal_id': rec.destination_journal_id.id,
                    'deposited_bank_id': rec.destination_journal_id.bank_id.id,
                    'deposited_date': rec.payment_date,
                    'partner_id': rec.company_id.id,
                })
                # vals['account_id'] = rec.check_ids.get_third_check_account().id
                vals['name'] = _('Deposit checks %s') % ', '.join(
                    rec.check_ids.mapped('name'))
        elif (rec.payment_method_code == 'transfer_check' and rec.payment_type == 'transfer'):
            _logger.info('Change Check')
            rec.transfer_check_ids._create_operation(
                'transfered', rec, False, date=rec.payment_date)
            for check in rec.transfer_check_ids:
                if check.type == 'third_check' and check.state == 'deposited':
                    check.write({
                        'deposited_journal_id': rec.destination_journal_id.id,
                        'deposited_bank_id': rec.destination_journal_id.bank_id.id,
                    })
                elif check.type == 'own_check' and check.state in ['use', 'debited']:
                    check.write({
                        'journal_id': rec.destination_journal_id.id,
                        'bank_id': rec.destination_journal_id.bank_id.id,
                    })

            vals['name'] = _('Transfered check %s') % ', '.join(
                rec.check_ids.mapped('name'))
        else:
            raise UserError(_(
                'This operatios is not implemented for checks:\n'
                '* Payment type: %s\n'
                '* Partner type: %s\n'
                '* Payment method: %s\n'
                '* Destination journal: %s\n' % (
                    rec.payment_type,
                    rec.partner_type,
                    rec.payment_method_code,
                    rec.destination_journal_id.type)))
        return vals



    def _get_liquidity_move_line_vals(self, amount):
        vals = super(AccountPayment, self)._get_liquidity_move_line_vals(
            amount)
        if self.payment_method_code == 'delivered_third_check' and not self.check_ids:
            raise UserError(_(
                'You can not make a payment with checks without associated checks.'))
        else:
            vals = self.do_checks_operations(vals=vals)
        return vals

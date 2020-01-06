# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError

class AccountRegisterPayments(models.TransientModel):
    _inherit = 'account.register.payments'

    @api.onchange('journal_id')
    def onchange_journal(self):
        res = super(AccountRegisterPayments, self)._onchange_journal()
        res['value'] = {'check_ids': []}
        return res

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        # Set payment method domain
        res = self._onchange_journal()
        if not res.get('domain', {}):
            res['domain'] = {}
        res['domain']['journal_id'] = self.payment_type == 'inbound' and [('at_least_one_inbound', '=', True)] or [('at_least_one_outbound', '=', True)]
        res['domain']['journal_id'].append(('type', 'in', ('bank', 'cash')))
        return res

    check_ids = fields.Many2many(
        'account.check',
        string='Cheques',
        copy=False,
    )
    # only for v8 comatibility where more than one check could be received
    # or ownd
    check_ids_copy = fields.Many2many(
        related='check_ids',
        readonly=True,
    )
    readonly_currency_id = fields.Many2one(
        related='currency_id',
        readonly=True,
    )
    readonly_amount = fields.Monetary(
        related='amount',
        readonly=True,
    )
    # we add this field for better usability on own checks and received
    # checks. We keep m2m field for backward compatibility where we allow to
    # use more than one check per payment
    check_id = fields.Many2one(
        'account.check',
        compute='_compute_check',
        string='Cheque',
    )

    @api.multi
    @api.depends('check_ids')
    def _compute_check(self):
        for rec in self:
            # we only show checks for own checks or received thid checks
            # if len of checks is 1
            if rec.payment_method_code in (
                    'received_third_check',
                    'own_check',) and len(rec.check_ids) == 1:
                rec.check_id = rec.check_ids[0].id

    # check fields, just to make it easy to load checks without need to create
    # them by a m2o record
    check_name = fields.Char(
        'Nombre del cheque',
        copy=False,
    )
    check_number = fields.Integer(
        'Número del cheque',
        copy=False
    )
    check_own_date = fields.Date(
        'Fecha del cheque',
        copy=False,
        default=fields.Date.context_today,
    )
    check_payment_date = fields.Date(
        'Fecha del pago de cheque',
        help="Only if this check is post dated",
    )
    checkbook_id = fields.Many2one(
        'account.checkbook',
        'Chequera',
    )
    check_subtype = fields.Selection(
        related='checkbook_id.own_check_subtype',
        readonly=True,
    )
    check_bank_id = fields.Many2one(
        'res.bank',
        'Banco del cheque',
        copy=False,
    )
    check_owner_vat = fields.Char(
        'Vat del emisor',
        copy=False,
    )
    check_owner_name = fields.Char(
        'Emisor',
        copy=False,
    )
    # this fields is to help with code and view
    check_type = fields.Char(
        compute='_compute_check_type',
    )
    checkbook_block_manual_number = fields.Boolean(
        related='checkbook_id.block_manual_number',
    )
    check_number_readonly = fields.Integer(
        related='check_number',
        readonly=True,
    )
    operation_no = fields.Char(string='Operation No.')

    @api.multi
    @api.depends('payment_method_code')
    def _compute_check_type(self):
        for rec in self:
            if rec.payment_method_code == 'own_check':
                rec.check_type = 'own_check'
            elif rec.payment_method_code in [
                    'received_third_check',
                    'received_third_check']:
                rec.check_type = 'third_check'


# on change methods

    # @api.constrains('check_ids')
    @api.onchange('check_ids', 'payment_method_code')
    def onchange_checks(self):
        # we only overwrite if payment method is delivered
        if self.payment_method_code == 'received_third_check':
            self.amount = sum(self.check_ids.mapped('amount'))

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
            if rec.payment_method_code in ['received_third_check']:
                if not rec.check_number:
                    check_name = False
                else:
                    check_name = _get_name_from_number(rec.check_number)
                rec.check_name = check_name
            elif rec.payment_method_code in ['own_check']:
                sequence = rec.checkbook_id.sequence_id
                if not rec.check_number:
                    check_name = False
                elif sequence:
                    if rec.check_number != sequence.number_next_actual:
                        sequence.write(
                            {'number_next_actual': rec.check_number})
                    check_name = rec.checkbook_id.sequence_id.next_by_id()
                else:
                    # in sipreco, for eg, no sequence on checkbooks
                    check_name = _get_name_from_number(rec.check_number)
                rec.check_name = check_name

    @api.onchange('check_own_date', 'check_payment_date')
    def onchange_date(self):
        if (
                self.check_own_date and self.check_payment_date and
                self.check_own_date > self.check_payment_date):
            self.check_payment_date = False
            raise UserError(
                _('Fecha de pago del cheque debe ser mayor a fecha del cheque'))

    @api.onchange('partner_id', 'payment_method_code')
    def onchange_partner_check(self):
        commercial_partner = self.partner_id.commercial_partner_id
        #Modificacion para v10. Preguntamos existencia de campo payment_method_code
        if self.payment_method_code:
            if self.payment_method_code == 'received_third_check':
                self.check_bank_id = (
                    commercial_partner.bank_ids and
                    commercial_partner.bank_ids[0].bank_id or False)
                self.check_owner_name = commercial_partner.name
                vat_field = 'vat'
                # to avoid needed of another module, we add this check to see
                # if l10n_ar cuit field is available
                if 'cuit' in commercial_partner._fields:
                    vat_field = 'cuit'
                self.check_owner_vat = commercial_partner[vat_field]
            elif self.payment_method_code == 'own_check':
                self.check_bank_id = self.journal_id.bank_id
                self.check_owner_name = False
                self.check_owner_vat = False

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

    @api.onchange('checkbook_id')
    def onchange_checkbook(self):
        if self.checkbook_id:
            self.check_number = self.checkbook_id.next_number

    @api.multi
    def create_payment(self):
        ctx = dict(self._context)
        payment_register_wzd = self
        ctx['register_payment'] = True
        ctx['payment_register_wzd'] = payment_register_wzd
        super(AccountRegisterPayments, self.with_context(ctx)).create_payment()

    def get_payment_vals(self):
        vals = super(AccountRegisterPayments, self).get_payment_vals()
        vals.update({
            'check_ids': [(4, check.id, None) for check in self.check_ids],
            'check_id': self.check_id.id,
            'check_name': self.check_name,
            'check_number': self.check_number,
            'check_own_date': self.check_own_date,
            'check_payment_date': self.check_payment_date,
            'checkbook_id': self.checkbook_id.id,
            'check_bank_id': self.check_bank_id.id,
            'check_owner_vat': self.check_owner_vat,
            'check_owner_name': self.check_owner_name,
        })
        return vals

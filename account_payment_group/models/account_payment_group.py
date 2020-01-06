# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


MAP_PARTNER_TYPE_ACCOUNT_TYPE = {
    'customer': 'receivable',
    'supplier': 'payable',
}
MAP_ACCOUNT_TYPE_PARTNER_TYPE = {
    'receivable': 'customer',
    'payable': 'supplier',
}
MAP_ACCOUNT_TYPE_CREDIT_PARTNER_TYPE = {
    'receivable': 'supplier',
    'payable': 'customer',
}
MAP_PARTNER_TYPE_CREDIT_ACCOUNT_TYPE = {
    'supplier': 'receivable',
    'customer': 'payable',
}

move_lines_domain = ("[('partner_id.commercial_partner_id', '=', commercial_partner_id),"
                     "('account_id.internal_type', '=', account_internal_type),"
                     "('account_id.reconcile', '=', True), ('reconciled', '=', False),('company_id', '=', company_id)]")


class AccountPaymentGroup(models.Model):
    _name = "account.payment.group"
    _description = "Payment group"
    _order = "date desc"
    _inherit = 'mail.thread'

    name = fields.Char(readonly=True, string='Group Payment', states={'draft': [('readonly', False)]},
                                                    copy=False, default=_("Draft Group Payment"))
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')])
    date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True,
                       # states={'draft': [('readonly', False)]},
                       help='This field is read only when payment lines already exist.')
    memo = fields.Char(string='Memo', readonly=True, translate=True, states={'draft': [('readonly', False)]})
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
                                 default=lambda self: self.env.user.company_id, readonly=True, translate=True,
                                 states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, readonly=True, translate=True,
                                 states={'draft': [('readonly', False)]})
    commercial_partner_id = fields.Many2one(related='partner_id.commercial_partner_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id, readonly=True,
                                  translate=True, states={'draft': [('readonly', False)]})
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    debt_move_line_ids = fields.Many2many('account.move.line', compute='_compute_debt_move_line_ids',
                                          inverse='_inverse_debt_move_line_ids', string="Debt Lines", translate=True,
                                          domain=move_lines_domain, readonly=True,
                                          states={'draft': [('readonly', False)]}) # help="Payment will be automatically matched with the oldest lines of this list (by date, no by maturity date). You can remove any line you dont want to be matched."
    to_pay_move_line_ids = fields.Many2many('account.move.line', 'account_move_line_payment_group_to_pay_rel',
                                            'payment_group_id', 'to_pay_line_id', string="To Pay Lines",
                                            translate=True, help='This lines are the ones the user has selected to be paid.',
                                            copy=False, domain=move_lines_domain, readonly=True,
                                            states={'draft': [('readonly', False)]}, sort='date_maturity')
    # advance_move_line_ids = fields.Many2many('account.move.line', string="Advance Lines")
    matched_move_line_ids = fields.Many2many('account.move.line', compute='_compute_matched_move_line_ids',
                                             help='Lines that has been matched to payments, only available after '
                                                  'payment validation')

    matched_amount = fields.Monetary(compute='compute_matched_amounts', currency_field='currency_id')
    unmatched_amount = fields.Monetary(compute='compute_matched_amounts', currency_field='currency_id')

    selected_finacial_debt = fields.Monetary(string='Selected Financial Debt', translate=True)
    selected_debt = fields.Monetary(string='Selected Debt', translate=True, compute='_compute_selected_debt')

    selected_debt_untaxed = fields.Monetary(string='Selected Debt Untaxed', translate=True,
                                            compute='_compute_selected_debt')

    invoiced_debt_untaxed = fields.Monetary(string='Invoice Debt Untaxed', translate=True,
                                            compute='_compute_selected_debt')
    unreconciled_amount = fields.Monetary(string='Adjusment / Advance', readonly=True, translate=True,
                                          states={'draft': [('readonly', False)]})
    to_pay_amount = fields.Monetary(string='To Pay Amount', readonly=True, translate=True,
                                    states={'draft': [('readonly', False)]})

    payments_amount = fields.Monetary(compute='_compute_payments_amount', string='Amount', translate=True)

    amount_payable = fields.Monetary(string='Amount payable')

    amount_payable_wtax = fields.Monetary(string='Amount payable With Tax', compute='_compute_payable_wtax')

    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('posted', 'Posted'), ('cancelled', 'Cancelled')],
                                readonly=True, default='draft', copy=False, string="Status",
                                track_visibility='onchange')

    payment_subtype = fields.Char(compute='_compute_payment_subtype')
    pop_up = fields.Boolean(compute='_compute_payment_pop_up', default=lambda x: x._context.get('pop_up', False))
    currency_rate = fields.Float(string='currency_rate')
    # manual_currency_rate = fields.Float(string='manual_currency_rate')
    # savedf = fields.Boolean(string='Savedf')
    # tot_in_currency = fields.Float(string='manual_currency_rate')
    currency2_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    payment_difference = fields.Monetary(compute='_compute_payment_difference', readonly=True, translate=True,
                                         string="Payment Difference")
    payment_ids = fields.One2many('account.payment', 'payment_group_id', string='Payment Lines', ondelete='cascade',
                                  copy=False, readonly=True, translate=True, states={'draft': [('readonly', False)],
                                                                                     'confirmed': [('readonly', False)]})
    move_line_ids = fields.One2many(related='payment_ids.move_line_ids', readonly=True, copy=False)
    account_internal_type = fields.Char(compute='_compute_account_internal_type')
    novatperc = fields.Boolean('No calcular retencion de IVA')
    has_paym_lines = fields.Boolean()
    # date2 = fields.Date()
    invoice_ids = fields.Many2many('account.invoice', string='Invoices')
    refund_invoice_ids = fields.Many2many('account.invoice', 'refund_invoice_payment_rel', 'payment_group_id', 'invoice_id', string='Refund Invoices')
    invoice_group_ids = fields.One2many('account.invoice.group',  'payment_group_id', string='Invoices')
    payment_difference_amount = fields.Monetary(compute='_compute_payment_difference_amount')
    payment_diff_amount_save = fields.Monetary(string='Payment difference amount', track_visibility='onchange')
    payment_difference_handling = fields.Selection([('open', 'Keep open'), ('reconcile', 'Mark invoice as fully paid')],
                                                   default='open', string="Payment Difference", copy=False)
    writeoff_account_id = fields.Many2one('account.account', string="Difference Account",
                                          domain=[('deprecated', '=', False)], copy=False)
    no_balance_account = fields.Boolean('Do not include advance payments.', default=False)
    writeoff_label = fields.Char(
        string='Journal Item Label',
        help='Change label of the counterpart that will hold the payment difference',
        default='Cerrar diferencia de pago')
    # localization = fields.Selection(related="company_id.localization")

    @api.multi
    @api.depends('state', 'payments_amount', 'matched_move_line_ids.payment_group_matched_amount')
    def compute_matched_amounts(self):
        for rec in self:
            if rec.state != 'posted':
                continue
            matched_amount = 0.0
            for line in rec.matched_move_line_ids.with_context(payment_group_id=rec.id):
                if rec.currency_id != rec.company_id.currency_id:
                    # matched_amount += line.company_id.currency_id.with_context(date=line.date).compute(line.payment_group_matched_amount, rec.currency_id)
                    matched_amount += line.company_id.currency_id._convert(line.payment_group_matched_amount,
                                                                           rec.currency_id, rec.company_id,
                                                                           line.date or fields.Date.today())
                else:
                    matched_amount += line.payment_group_matched_amount

            rec.matched_amount = matched_amount
            # rec.unmatched_amount = rec.payments_amount - rec.matched_amount
            if rec.payment_difference_handling == 'reconcile':
                rec.unmatched_amount = 0.0
            else:
                rec.unmatched_amount = rec.payments_amount - rec.matched_amount

    @api.multi
    @api.depends('to_pay_move_line_ids')
    def _compute_debt_move_line_ids(self):
        for rec in self:
            rec.debt_move_line_ids = rec.to_pay_move_line_ids


    @api.multi
    @api.onchange('debt_move_line_ids', 'debt_move_line_ids.amount_residual_update')
    def _inverse_debt_move_line_ids(self):
        for rec in self:
            rec.to_pay_move_line_ids = rec.debt_move_line_ids.sorted(key='date_maturity')

    @api.multi
    def _compute_payment_pop_up(self):
        pop_up = self._context.get('pop_up', False)
        for rec in self:
            rec.pop_up = pop_up

    @api.multi
    @api.depends('company_id.double_validation', 'partner_type')
    def _compute_payment_subtype(self):
        for rec in self:
            payment_subtype = 'simple'
            rec.payment_subtype = payment_subtype

    @api.one
    def _compute_matched_move_line_ids(self):
        ids = []
        for aml in self.payment_ids.mapped('move_line_ids'):
            if aml.account_id.reconcile:
                ids.extend(
                    [r.debit_move_id.id for r in aml.matched_debit_ids] if
                    aml.credit > 0 else [
                        r.credit_move_id.id for r in aml.matched_credit_ids])
        self.matched_move_line_ids = self.env['account.move.line'].browse(
            list(set(ids)))

    @api.multi
    @api.depends('partner_type')
    def _compute_account_internal_type(self):
        for rec in self:
            if rec.partner_type:
                rec.account_internal_type = MAP_PARTNER_TYPE_ACCOUNT_TYPE[
                    rec.partner_type]

    @api.multi
    @api.depends('to_pay_amount', 'payments_amount', 'amount_payable')
    def _compute_payment_difference(self):
        for rec in self:
            rec.payment_difference = rec.to_pay_amount - rec.payments_amount

    @api.multi
    @api.depends('selected_debt', 'amount_payable')
    def _compute_payment_difference_amount(self):
        for rec in self:
            payment_difference_amount = rec.selected_debt - rec.amount_payable
            rec.payment_difference_amount = -payment_difference_amount if rec.partner_type == 'supplier' else payment_difference_amount

    @api.multi
    @api.onchange('unreconciled_amount', 'amount_payable')
    def _onchange_to_pay_amount(self):
        for rec in self:
            rec.to_pay_amount = rec.amount_payable + self.unreconciled_amount

    @api.multi
    @api.depends('payment_ids','date')
    @api.onchange('payment_ids','date')
    def _onchange_payment_ids(self):
        for rec in self:
            if rec.payment_ids:
                rec.has_paym_lines = True
            else:
                rec.has_paym_lines = False
            # rec.date2 = rec.date

    @api.multi
    @api.depends('payment_ids.amount')
    def _compute_payments_amount(self):
        for rec in self:
            amount = 0.0
            for line in rec.payment_ids:
                if rec.currency_id != line.currency_id:
                    # amount += line.currency_id.with_context(date=rec.date).compute(line.amount, rec.currency_id)
                    amount += line.currency_id._convert(line.amount, rec.currency_id, rec.company_id,
                                                        rec.date or fields.Date.today())
                else:
                    amount += line.amount
            rec.payments_amount = amount

    @api.model
    @api.onchange('date')
    def onchange_date(self):
        for pg in self:
            for pay in pg.payment_ids:
                pay.payment_date = pg.date

            if pg.payment_ids:
                raise UserError(_("To change the date of the Receipt there must not be any Payment Lines loaded."))

    def _get_invoiced_debt_untaxed(self, move_line):
        payment_group_balance_amount = 0.0
        payment_group_id = self
        if not payment_group_id:
            return 0.0
        payments = self.env['account.payment.group'].browse(payment_group_id.id).payment_ids
        payment_move_lines = payments.mapped('move_line_ids')
        payment_partial_lines = self.env[
            'account.partial.reconcile'].search([
                '|',
                ('credit_move_id', 'in', payment_move_lines.ids),
                ('debit_move_id', 'in', payment_move_lines.ids),
            ])
        for rec in move_line:
            balance_amount = 0.0
            for pl in (rec.matched_debit_ids + rec.matched_credit_ids):
                if pl in payment_partial_lines:
                    balance_amount += pl.amount
            payment_group_balance_amount = balance_amount

        return payment_group_balance_amount

    def _getuntaxedvalue(self,invoice,am,acc_ids_list=[],withholding_amount_type=''):
        res = res_nc = 0.0
        inv_orig = ''
        tot_nc = 0.0
        if invoice:
            for line in invoice.invoice_line_ids:
                if withholding_amount_type == 'untaxed_amount':
                    if line.account_id.id in acc_ids_list or not acc_ids_list:
                        res +=  line.price_subtotal
                elif withholding_amount_type == 'vat_amount':
                    if line.account_id.id in acc_ids_list or not acc_ids_list:
                        for taxline in line.invoice_line_tax_ids:
                            if taxline.tax_group_id.tax == 'vat':
                                res += taxline.amount * line.price_subtotal / 100
                elif withholding_amount_type == 'total_amount':
                    if line.account_id.id in acc_ids_list or not acc_ids_list:
                        for taxline in line.invoice_line_tax_ids:
                            if taxline.tax_group_id.tax == 'vat':
                                res += taxline.amount * line.price_subtotal / 100
                        res += line.price_subtotal
            inv_orig_g = self.env['account.invoice'].search(
                [('nc_ref_id','=',invoice.nc_ref_id), ('state', '=', 'paid'), ('type','in', ['in_refund','in_invoice'])]
            )

            if inv_orig_g:
                for inv_orig in inv_orig_g:
                    for line in inv_orig.invoice_line_ids:
                        if withholding_amount_type == 'untaxed_amount':
                            if line.account_id.id in acc_ids_list or not acc_ids_list:
                                res_nc += line.price_subtotal
                        elif withholding_amount_type == 'vat_amount':
                            if line.account_id.id in acc_ids_list or not acc_ids_list:
                                for taxline in line.invoice_line_tax_ids:
                                    if taxline.tax_group_id.tax == 'vat':
                                        res_nc += taxline.amount * line.price_subtotal / 100
                        elif withholding_amount_type == 'total_amount':
                            if line.account_id.id in acc_ids_list or not acc_ids_list:
                                for taxline in line.invoice_line_tax_ids:
                                    if taxline.tax_group_id.tax == 'vat':
                                        res_nc += taxline.amount * line.price_subtotal / 100
                                res_nc += line.price_subtotal
                    tot_nc += inv_orig.amount_total
                res -= res_nc
                if res < 0:
                    res = 0
                    raise UserError(_("According to the established accounts, there is more credit than debit, check NC"))

            #print 'res ', res
            tot_am = invoice.amount_total
            if inv_orig_g:
                tot_am -= tot_nc
            if tot_am > 0:
                perc = am * 100 / tot_am
            else:
                perc = 0
            res = (res * perc / 100)
        return res

    @api.onchange('invoice_group_ids')
    def onchange_invoice_group_ids(self):
        invoice_ids = self.invoice_group_ids.mapped('invoice_id')
        moves = self.env['account.move.line']
        for move in self.to_pay_move_line_ids:
            if not move.invoice_id or move.invoice_id in invoice_ids or (
                                        move.invoice_id.type in ['out_refund', 'in_refund']
                                        and move.invoice_id.refund_type == 'credit'):
                moves += move
        invoices = self.env['account.invoice']
        for invoice in self.invoice_ids:
            if invoice in invoice_ids:
                invoices += invoice
        self.debt_move_line_ids = moves
        self.invoice_ids = invoices
        self._onchange_amount_payable()

    @api.onchange('invoice_group_ids', 'refund_invoice_ids')
    def onchange_invoice_group_ids(self):
        invoice_ids = self.invoice_group_ids.mapped('invoice_id')
        moves = self.env['account.move.line']
        for move in self.to_pay_move_line_ids:
            if not move.invoice_id or move.invoice_id in invoice_ids or move.invoice_id in self.refund_invoice_ids:
                moves += move
        invoices = self.env['account.invoice']
        for invoice in self.invoice_ids:
            if invoice in invoice_ids:
                invoices += invoice
        self.debt_move_line_ids = moves
        self.invoice_ids = invoices
        self._onchange_amount_payable()

    @api.onchange('debt_move_line_ids')
    def onchange_debt_move_line_ids(self):
        invoice_ids = self.debt_move_line_ids.mapped('invoice_id')
        groups = self.env['account.invoice.group']
        for group in self.invoice_group_ids:
            if group.invoice_id in invoice_ids:
                groups += group
        invoices = self.env['account.invoice']
        for invoice in self.invoice_ids:
            if invoice in invoice_ids:
                invoices += invoice

        refund_invoice_ids = self.env['account.invoice']
        for refund in self.refund_invoice_ids:
            if refund in invoice_ids:
                refund_invoice_ids += refund

        self.invoice_group_ids = groups
        self.invoice_ids = invoices
        self.refund_invoice_ids = refund_invoice_ids
        self._onchange_amount_payable()

    @api.one
    @api.depends('to_pay_move_line_ids', 'invoice_group_ids.advance_amount',
                 'to_pay_move_line_ids.amount_residual',
                 'currency_id', 'to_pay_move_line_ids.amount_residual_currency')
    def _compute_selected_debt(self):

        selected_debt = selected_debt_untaxed = invoiced_debt_untaxed = 0.0
        if self.state != 'posted':
            pay_amt = self.to_pay_amount
        else:
            pay_amt = self.payments_amount
        use_currency = False
        if self.currency_id != self.company_id.currency_id:
            use_currency = True

        sign = self.partner_type == 'supplier' and -1.0 or 1.0
        #self.to_pay_move_line_ids = self.to_pay_move_line_ids.sorted(key='date_maturity')
        rest_paym = paymt = payp = 0.0
        for line in self.to_pay_move_line_ids.sorted(key='date_maturity'):
            untax_amt = 0.0
            invoice_group_id = self.invoice_group_ids.filtered(lambda x: x.invoice_id == line.invoice_id)
            if line.invoice_id and invoice_group_id.mapped('invoice_id'):
                if use_currency and self.currency_id == line.currency_id:
                    selected_debt += invoice_group_id.advance_amount * sign
                elif use_currency and line.currency_id and self.currency_id != line.currency_id:
                    # selected_debt += self.company_id.currency_id.with_context(date=self.date).compute(
                    #     invoice_group_id.advance_amount, self.currency_id) * sign
                    selected_debt += self.company_id.currency_id._convert(invoice_group_id.advance_amount,
                                                                          self.currency_id, self.company_id,
                                                                          self.date or fields.Date.today()) * sign
                else:
                    selected_debt += invoice_group_id.advance_amount_company * sign
            elif use_currency and self.currency_id == line.currency_id:
                selected_debt += line.amount_residual_currency

            elif use_currency and line.currency_id and self.currency_id != line.currency_id:
                # selected_debt += self.company_id.currency_id.with_context(date=self.date).compute(line.amount_residual, self.currency_id)
                selected_debt += self.company_id.currency_id._convert(line.amount_residual, self.currency_id,
                                                                      self.company_id, self.date or fields.Date.today())
            else:
                selected_debt += line.amount_residual

            invoice = line.invoice_id
            invoice_sign = invoice.type in ['in_refund'] and -1.0 or 1.0
            if rest_paym < pay_amt:
                if self.state != 'posted':
                    if use_currency:
                        paym = -line.amount_residual_currency
                    else:
                        paym = -line.amount_residual_update

                else:
                    paym = self._get_invoiced_debt_untaxed(line)
                paymt += paym
                if  paymt <= pay_amt:
                    rest_paym += paym
                    payp =  paym
                else:
                    payp =  pay_amt - rest_paym
                    rest_paym += pay_amt - rest_paym
                to_pay_amount = -(payp * sign)
                untax_amt = self._getuntaxedvalue(line.invoice_id, to_pay_amount)
            untax_amt = untax_amt * invoice_sign
            invoiced_debt_untaxed += untax_amt

        self.selected_debt = selected_debt * sign
        self.selected_debt_untaxed = invoiced_debt_untaxed
        #self._onchange_selected_debt()

    # @api.multi
    # @api.onchange('to_pay_move_line_ids', 'amount_payable')
    # def _onchange_to_pay_amount(self):
    #     for rec in self.sudo():
    #         rec.to_pay_amount = rec.amount_payable + rec.unreconciled_amount

    @api.multi
    @api.onchange('selected_debt', 'currency_id')
    def _onchange_amount_payable(self):
        for rec in self:
            rec.amount_payable = rec.selected_debt if rec.selected_debt > 0.0 else 0.0

    @api.multi
    @api.onchange('no_balance_account')
    def _onchange_no_balance_account(self):
        for rec in self:
            if rec.no_balance_account:
                if rec.partner_type == 'customer':
                    lines_del = rec.debt_move_line_ids.filtered(lambda x: x.credit > 0.0)
                else:
                    lines_del = rec.debt_move_line_ids.filtered(lambda x: x.debit > 0.0)
                rec.debt_move_line_ids -= lines_del
            else:
                rec.add_lines_balance()

    @api.multi
    @api.depends('amount_payable')
    def _compute_payable_wtax(self):
        for rec in self:
            rec.amount_payable_wtax = 0.0

    @api.multi
    def onchange(self, values, field_name, field_onchange):
        field_onchange_value = field_onchange.copy()
        for field in field_onchange.keys():
            if field.startswith(('to_pay_move_line_ids.','debt_move_line_ids.')):
                del field_onchange_value[field]
        return super(AccountPaymentGroup, self).onchange(values, field_name, field_onchange_value)

    @api.multi
    @api.depends('amount_payable', 'unreconciled_amount', 'partner_id')
    def _compute_to_pay_amount(self):
        for rec in self:
            rec.to_pay_amount = rec.amount_payable + rec.unreconciled_amount

    @api.multi
    def _inverse_to_pay_amount(self):
        for rec in self:
            rec.unreconciled_amount = rec.to_pay_amount - rec.amount_payable

    @api.onchange('partner_id', 'partner_type', 'company_id')
    def _refresh_payments_and_move_lines(self):
        if self._context.get('pop_up'):
            return
        self.invalidate_cache(['payment_ids'])
        self.payment_ids = self.env['account.payment']
        self.to_pay_move_line_ids = self.env['account.move.line']
        #self.payment_ids.unlink()
        #self.to_pay_move_line_ids.unlink()
        self.add_all()
        #self._compute_to_pay_amount()

    @api.multi
    def add_lines_balance(self):
        for rec in self:
            domain = [
                ('partner_id.commercial_partner_id', '=',
                 rec.commercial_partner_id.id),
                ('account_id.internal_type', '=',
                 rec.account_internal_type),
                ('account_id.reconcile', '=', True),
                ('reconciled', '=', False),
                ('company_id', '=', rec.company_id.id),
            ]
            if rec.no_balance_account:
                if rec.partner_type == 'customer':
                    domain.append(('debit', '>', 0.0))
                else:
                    domain.append(('credit', '>', 0.0))
            to_pay_move_line_ids = rec.env['account.move.line'].search(
                domain, order='date_maturity')
            if rec.invoice_group_ids:
                invoices = rec.invoice_group_ids.mapped('invoice_id')
                for move_line in to_pay_move_line_ids:
                    if move_line.invoice_id and move_line.invoice_id not in invoices:
                        to_pay_move_line_ids -= move_line
            rec.to_pay_move_line_ids = to_pay_move_line_ids

    @api.multi
    def add_all(self):
        for rec in self:
            domain = [
                ('partner_id.commercial_partner_id', '=',
                    rec.commercial_partner_id.id),
                ('account_id.internal_type', '=',
                    rec.account_internal_type),
                ('account_id.reconcile', '=', True),
                ('reconciled', '=', False),
                ('company_id', '=', rec.company_id.id),
                ('move_id.state', '=', 'posted'),
                # ('currency_id', 'in', rec.currency_id != rec.company_id.currency_id and [rec.currency_id] and [rec.currency_id.id] or [rec.company_id.currency_id.id, False])
            ]
            if rec.no_balance_account:
                if rec.partner_type == 'customer':
                    domain.append(('debit', '>', 0.0))
                else:
                    domain.append(('credit', '>', 0.0))
            rec.to_pay_move_line_ids = rec.env['account.move.line'].search(
                domain, order='date_maturity')
            type_domain = {'sale': ['out_refund', 'out_invoice'], 'purchase': ['in_refund', 'in_invoice']}
            invoice_ids = rec.to_pay_move_line_ids.mapped('invoice_id').filtered(
                                lambda x: x.type in ['in_invoice', 'out_invoice'] or (x.type in ['out_refund', 'in_refund']
                                                                                      and x.refund_type == 'debit'))
            rec.invoice_ids = invoice_ids
            refund_invoice_ids = rec.to_pay_move_line_ids.mapped('invoice_id').filtered(
                lambda x: x.type in ['out_refund', 'in_refund'] and x.refund_type == 'credit')
            rec.refund_invoice_ids = refund_invoice_ids
            invoice_group_lines = self.env['account.invoice.group']
            for invoice in invoice_ids:
                invoice_group_lines += self.env['account.invoice.group'].create({
                                            'invoice_id': invoice.id,
                                            'number': invoice.number,
                                            'partner_id': invoice.partner_id.id,
                                            'date': invoice.date,
                                            'num_comprobante': invoice.num_comprobante,
                                            'tipo_comprobante': invoice.tipo_comprobante.id,
                                            'currency_id': invoice.currency_id.id,
                                            'company_id': invoice.company_id.id,
                                            'company_currency_id': invoice.company_id.currency_id.id,
                                            # 'payment_group_id': rec.id,
                                            'advance_amount': invoice.residual,
                                            # 'advance_amount_company':  invoice.company_id.currency_id.with_context(
                                            #                                     date=invoice.date).compute(
                                            #                                  invoice.residual,  invoice.currency_id),
                                            })
            rec.invoice_group_ids = invoice_group_lines
            self._onchange_amount_payable()

    @api.multi
    def remove_all(self):
        self.to_pay_move_line_ids = False
        self.onchange_debt_move_line_ids()
        self._onchange_amount_payable()

    @api.model
    def default_get(self, fields):
        # TODO si usamos los move lines esto no haria falta
        rec = super(AccountPaymentGroup, self).default_get(fields)
        to_pay_move_line_ids = self._context.get('to_pay_move_line_ids')
        to_pay_move_lines = self.env['account.move.line'].browse(
            to_pay_move_line_ids).filtered(lambda x: (
                x.account_id.reconcile and
                x.account_id.internal_type in ('receivable', 'payable')))
        if to_pay_move_lines:
            partner = to_pay_move_lines.mapped('partner_id')
            if len(partner) != 1:
                raise ValidationError(_(
                    'You can not send to pay lines from different partners'))

            internal_type = to_pay_move_lines.mapped(
                'account_id.internal_type')
            if len(internal_type) != 1:
                raise ValidationError(_(
                    'You can not send to pay lines from different partners'))
            rec['partner_id'] = partner[0].id
            rec['partner_type'] = MAP_ACCOUNT_TYPE_PARTNER_TYPE[
                internal_type[0]]
            rec['to_pay_move_line_ids'] = [(6, False, to_pay_move_line_ids)]

        invoice_ids = self._context.get('invoice_ids')
        if invoice_ids:
            # rec['invoice_ids'] = [(6, 0, invoice_ids)]
            invoices = self.env['account.invoice'].browse(invoice_ids)
            invoice_filter = invoices.filtered(lambda x: x.type in ['in_invoice', 'out_invoice'] or \
                                                         (x.type in ['out_refund', 'in_refund']
                                                                                      and x.refund_type == 'debit'))
            credit_filter = invoices.filtered(
                lambda x: x.type in ['out_refund', 'in_refund'] and x.refund_type == 'credit')
            rec['invoice_ids'] = [(6, 0, invoice_filter.ids)]
            rec['refund_invoice_ids'] = [(6, 0, credit_filter.ids)]
            if invoice_filter and credit_filter:
                raise ValidationError(_(
                    'You cannot send to pay credit notes with invoices and debit notes.'))
            invoice_group_lines = self.env['account.invoice.group']
            for invoice in invoice_filter:
                invoice_group_lines += self.env['account.invoice.group'].create({
                    'invoice_id': invoice.id,
                    'number': invoice.number,
                    'partner_id': invoice.partner_id.id,
                    'date': invoice.date,
                    'num_comprobante': invoice.num_comprobante,
                    'tipo_comprobante': invoice.tipo_comprobante.id,
                    'currency_id': invoice.currency_id.id,
                    'company_id': invoice.company_id.id,
                    'company_currency_id': invoice.company_id.currency_id.id,
                    # 'payment_group_id': rec.id,
                    'advance_amount': invoice.residual,
                    # 'advance_amount_company':  invoice.company_id.currency_id.with_context(date=invoice.date).compute(invoice.residual,
                    #                                                                             invoice.currency_id),
                })
            rec['invoice_group_ids'] = [(6, 0, invoice_group_lines.ids)]
            currency_ids = invoices.mapped('currency_id')
            if invoices.filtered(
                    lambda x: x.partner_id.id != invoices[0].partner_id.id):
                raise ValidationError(_(
                    'You can not send to pay lines from different partners'))
            to_pay_move_lines = invoices.mapped('open_move_line_ids').filtered(lambda x: (
                                                            x.account_id.reconcile and
                                                            x.account_id.internal_type in ('receivable', 'payable')))
            internal_type = []
            for t in to_pay_move_lines.mapped('account_id.internal_type'):
                if t not in internal_type:
                    internal_type.append(t)
            if len(internal_type) != 1:
                raise ValidationError(_(
                    'You can not send to pay lines from different type account or different receivable or payable.'))
            if len(currency_ids) == 1:
                rec['currency_id'] = currency_ids[0].id
            rec['partner_id'] = invoices[0].partner_id.id
            if not invoice_filter and credit_filter:
                rec['partner_type'] = MAP_ACCOUNT_TYPE_CREDIT_PARTNER_TYPE[internal_type[0]]
            else:
                rec['partner_type'] = MAP_ACCOUNT_TYPE_PARTNER_TYPE[internal_type[0]]
            rec['to_pay_move_line_ids'] = [(6, 0, to_pay_move_lines.ids)]
            rec['company_id'] = invoices[0].company_id.id

        return rec

    @api.multi
    def update_invoice_group_ids(self):
        for rec in self:
            if rec.state == 'posted':
                invoice_move_ids = rec.matched_move_line_ids.with_context(payment_group_id=rec.id).mapped('invoice_id')
            else:
                invoice_move_ids = rec.debt_move_line_ids.mapped('invoice_id')
            invoice_ids = invoice_move_ids.filtered(lambda x: x.type in ['in_invoice', 'out_invoice'] or
                                                              (x.type in ['out_refund', 'in_refund']
                                                               and x.refund_type == 'debit'))
            refund_invoice_ids = invoice_move_ids.filtered(lambda x: x.type in ['out_refund', 'in_refund']
                                                                and x.refund_type == 'credit')
            groups = rec.invoice_group_ids.filtered(lambda x: x.invoice_id in invoice_ids)
            invoice_no_group = invoice_ids.filtered(lambda x: x not in groups.mapped('invoice_id'))
            for inv in invoice_no_group:
                if rec.state == 'posted':
                    move = rec.matched_move_line_ids.with_context(payment_group_id=rec.id).filtered(lambda x: x.invoice_id == inv)
                    if (move.currency_id and move.currency_id != move.company_id.currency_id) or \
                            (move.invoice_id.company_id.currency_id != move.invoice_id.currency_id):
                        currency_id = move.currency_id or move.invoice_id.currency_id
                        advance_amount = move.company_id.currency_id._convert(move.payment_group_matched_amount,
                                                                              currency_id,
                                                                              move.company_id,
                                                                              move.date or fields.Date.today())
                    else:
                        advance_amount = move.payment_group_matched_amount
                else:
                    advance_amount = inv.amount_residual
                groups += self.env['account.invoice.group'].create({
                    'invoice_id': inv.id,
                    'number': inv.number,
                    'partner_id': inv.partner_id.id,
                    'date': inv.date,
                    'num_comprobante': inv.num_comprobante,
                    'tipo_comprobante': inv.tipo_comprobante.id,
                    'currency_id': inv.currency_id.id,
                    'company_id': inv.company_id.id,
                    'company_currency_id': inv.company_id.currency_id.id,
                    # 'payment_group_id': rec.id,
                    'advance_amount': advance_amount,
                    # 'advance_amount_company': rec.state == 'posted' and 0.0 or inv.company_id.currency_id.with_context(
                    #     date=inv.date).compute(
                    #     inv.residual, inv.currency_id),
                })
            rec.invoice_group_ids = groups
            rec.invoice_ids = rec.invoice_group_ids.mapped('invoice_id')
            rec.refund_invoice_ids = refund_invoice_ids

    def update_group_advance_move(self):
        for rec in self:
            group = self.env['payment.group.advance.move']
            if rec.state == 'posted':
                moves = rec.matched_move_line_ids.with_context(payment_group_id=rec.id).filtered(lambda x: x.invoice_id)
            else:
                moves = rec.debt_move_line_ids.filtered(lambda x: x.invoice_id)
            for move in moves:
                payments = self.env['payment.group.advance.move'].search([('move_line_id', '=', move.id),
                                                                          ('payment_group_id', '=', rec.id)])
                if rec.state == 'draft':
                    payments.unlink()
                else:
                    if not payments:
                        val_group_move = {
                            'move_line_id': move.id, 'payment_group_id': rec.id,
                            'currency_id': rec.company_id.currency_id.id,
                            'payment_group_advance_amount': -1.00 * move.payment_group_matched_amount,
                            'pg_advance_amount_currency': -1.00 * move.payment_group_matched_amount
                        }
                        if (move.currency_id and move.currency_id != move.company_id.currency_id) or \
                                (move.invoice_id.company_id.currency_id != move.invoice_id.currency_id):
                            currency_id = move.currency_id or move.invoice_id.currency_id
                            paid_amount_currency = move.company_id.currency_id._convert(move.payment_group_matched_amount,
                                                                                  currency_id,
                                                                                  move.company_id,
                                                                                  move.date or fields.Date.today())
                            val_group_move['other_currency_id'] = currency_id.id
                            val_group_move['pg_advance_amount_currency'] = -1.00 * paid_amount_currency
                        group.create(val_group_move)

    @api.multi
    def button_journal_entries(self):
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('payment_id', 'in', self.payment_ids.ids)],
        }

    @api.multi
    def button_journal_entry(self):
        moves = self.env['account.move.line'].search([('payment_group_id', 'in', self.ids)]).mapped('move_id.id')
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', moves)],
        }

    @api.multi
    def unreconcile(self):
        for rec in self:
            rec.payment_ids.unreconcile()
            # TODO en alguos casos setear sent como en payment?
            rec.write({'state': 'posted'})

    @api.multi
    def cancel(self):
        for rec in self:
            if rec.state != 'confirmed':
                for line in rec.matched_move_line_ids:
                    payments = self.env['payment.group.advance.move'].search([('move_line_id', '=', line.id),
                                                                              ('payment_group_id', '=', rec.id)])
                    payments.unlink()
                move_lines = rec.payment_ids.mapped('move_line_ids')
                if move_lines:
                    move_lines.remove_move_reconcile()
                    for move in move_lines.mapped('move_id'):
                        # move.line_ids.remove_move_reconcile()
                        move.button_cancel()
                        move.unlink()

                rec.payment_ids.write({
                    'state': 'cancelled',
                    'move_name': False,
                })
                rec.payment_ids.cancel_check()
            rec.state = 'cancelled'

    @api.multi
    def draft(self):
        for rec in self:
            rec.payment_ids.filtered(lambda x: x.state == 'cancelled').action_draft()
            rec.state = 'draft'

    @api.multi
    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_(
                "You can not delete a payment that is already posted"))
        return super(AccountPaymentGroup, self).unlink()

    @api.multi
    def confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    @api.model
    def create(self, values):
        self.clear_caches()
        res = super(AccountPaymentGroup, self.with_context(draft_validation=True)).create(values)
        # res.date = res.date2
        return res

    def generate_withholding_payments(self):
        return self

    def create_withholding(self):
        return True

    @api.multi
    def post(self):
        self = self.generate_withholding_payments()
        for rec in self:
            rec.payment_ids.write({'payment_date': self.date})
            if float_compare(rec.amount_payable, rec.payments_amount, precision_rounding=rec.currency_id.rounding) != 0:
                raise ValidationError(_(
                    'The total amount to be paid must match the sum of the amount of the payments to be executed!'))
            if not rec.payment_ids:
                raise ValidationError(_(
                    'You can not confirm a payment group without payment '
                    'lines!'))
            if (rec.payment_subtype == 'double_validation' and
                    rec.payment_difference):
                raise ValidationError(_(
                    'To Pay Amount and Payment Amount must be equal!'))

            writeoff_acc_id = False
            writeoff_journal_id = False

            if rec.company_id.arg_sortdate:
                rec.to_pay_move_line_ids = rec.to_pay_move_line_ids.sorted(key='date_maturity')

            if rec.payment_difference_handling == 'reconcile':
                # payment_diff = rec.payment_ids.sorted(key=lambda i:i.amount, reverse=True)[0]
                # payment_diff.payment_difference_amount = rec.payment_difference_amount
                payment_curr = rec.payment_ids.filtered(lambda x: x.currency_id == rec.currency_id)
                if payment_curr:
                    payment_diff = payment_curr.sorted(key=lambda i: i.amount, reverse=True)[0]
                else:
                    payment_diff = rec.payment_ids.sorted(key=lambda i: i.amount, reverse=True)[0]
                if rec.currency_id != payment_diff.currency_id:
                    # payment_diff.payment_difference_amount = rec.currency_id.with_context(date=self.date).compute(
                    #     rec.payment_difference_amount, payment_diff.currency_id)
                    payment_diff.payment_difference_amount = rec.currency_id._convert(rec.payment_difference_amount,
                                                                                      payment_diff.currency_id,
                                                                                      self.company_id,
                                                                                      self.date or fields.Date.today())
                else:
                    payment_diff.payment_difference_amount = rec.payment_difference_amount
                rec.payment_diff_amount_save = rec.payment_difference_amount if rec.payment_difference_amount > 0 else rec.payment_difference_amount * -1
                payment_diff.payment_difference_handling = rec.payment_difference_handling
                payment_diff.writeoff_account_id = rec.writeoff_account_id.id
                payment_diff.writeoff_label = rec.writeoff_label
                payment_diff.invoice_ids = rec.invoice_ids.ids

            rec.payment_ids.with_context(no_reconcile=True).post()
            counterpart_aml = rec.payment_ids.mapped('move_line_ids').filtered(
                lambda r: not r.reconciled and r.account_id.internal_type in (
                    'payable', 'receivable'))
            residual_amount = {}
            residual_amount_currency = {}
            for move_line in rec.to_pay_move_line_ids:
                residual_amount[str(move_line.id)] = move_line.amount_residual
                residual_amount_currency[str(move_line.id)] = move_line.amount_residual_currency

            rec.to_pay_move_line_ids.sorted(key=lambda p: (p.date, p.id)).with_context(
                field_reconcile='amount_residual_update', payment_group_id=rec.id).reconcile(writeoff_acc_id, writeoff_journal_id)
            for pay in counterpart_aml:
                (pay + (rec.to_pay_move_line_ids.with_context(payment_group_id=rec.id).filtered(lambda x:x.amount_residual_update != 0.0).sorted(
                    key=lambda p: (p.date, p.id)))).with_context(
                    field_reconcile='amount_residual_update', payment_group_id=rec.id).reconcile(writeoff_acc_id, writeoff_journal_id)

            group_move_obj = self.env['payment.group.advance.move']
            advance_move = rec.to_pay_move_line_ids - rec.matched_move_line_ids
            for move_line in rec.to_pay_move_line_ids:
                paid_amount = residual_amount[str(move_line.id)] - move_line.amount_residual
                if paid_amount != 0:
                    val_group_move = {
                        'move_line_id': move_line.id, 'payment_group_id': rec.id,
                        'currency_id': rec.company_id.currency_id.id,
                        'payment_group_advance_amount': -1.00 * paid_amount,
                        'pg_advance_amount_currency': -1.00 * paid_amount
                    }
                    if move_line.currency_id != rec.company_id.currency_id:
                        paid_amount_currency = residual_amount_currency[
                                                   str(move_line.id)] - move_line.amount_residual_currency
                        val_group_move['other_currency_id'] = move_line.currency_id.id
                        val_group_move['pg_advance_amount_currency'] = -1.00 * paid_amount_currency
                    group_move_obj.create(val_group_move)

            sequence_name = rec.get_sequence_name()
            if sequence_name:
                rec.name = sequence_name[0]
            rec.state = 'posted'
        self.create_withholding()


    @api.one
    def get_sequence_name(self):
        if self.partner_type == 'supplier':
            return self.env['ir.sequence'].with_context(ir_sequence_date=self.date).next_by_code(
                'account.payment.group')
        else:
            return self.env['ir.sequence'].with_context(ir_sequence_date=self.date).next_by_code(
                'account.payment.group.receiver')

    @api.multi
    def is_exist_check(self, payments):
        for payment in payments:
            if payment.check_ids:
                return True
        return False

    @api.one
    def get_inv_show_report_currency(self):
        show_report_currency = 'company_currency'
        if self.state == 'posted':
            if self.matched_move_line_ids:
                currencies = self.matched_move_line_ids.mapped('currency_id')
                if currencies.filtered(lambda x: x != currencies[0]):
                    show_report_currency = 'multi_currency'
                elif currencies.filtered(lambda x: x != self.company_id.currency_id):
                    show_report_currency = 'other_currency'
        else:
            if self.debt_move_line_ids:
                currencies = self.debt_move_line_ids.mapped('currency_id')
                if currencies.filtered(lambda x: x != currencies[0]):
                    show_report_currency = 'multi_currency'
                elif currencies.filtered(lambda x: x != self.company_id.currency_id):
                    show_report_currency = 'other_currency'
        return show_report_currency

    @api.one
    def get_pay_show_report_currency(self):
        show_report_currency = 'company_currency'
        if self.payment_ids:
            currencies = self.payment_ids.mapped('currency_id')
            if currencies.filtered(lambda x: x != currencies[0]):
                show_report_currency = 'multi_currency'
            elif currencies.filtered(lambda x: x != self.company_id.currency_id):
                show_report_currency = 'other_currency'
        return show_report_currency

    @api.one
    def get_amount_currency(self):
        if self.company_id.currency_id != self.currency_id:
            # return self.currency_id.with_context(date=self.date).compute(
            #     self.amount_total_payable, self.company_id.currency_id)
            return self.currency_id._convert(self.amount_payable, self.company_id.currency_id, self.company_id,
                                             self.date or fields.Date.today())

        else:
            return self.amount_payable

    @api.one
    def get_unmatched_amount_currency(self):
        if self.company_id.currency_id != self.currency_id:
            # return self.currency_id.with_context(date=self.date).compute(
            #     self.unmatched_amount, self.company_id.currency_id)
            return self.currency_id._convert(self.unmatched_amount, self.company_id.currency_id, self.company_id,
                                             self.date or fields.Date.today())
        else:
            return self.unmatched_amount

    @api.one
    def get_payment_difference_amount_currency(self):
        if self.company_id.currency_id != self.currency_id:
            # return self.currency_id.with_context(date=self.date).compute(
            #     self.payment_diff_amount_save, self.company_id.currency_id)
            return self.currency_id._convert(self.payment_diff_amount_save, self.company_id.currency_id, self.company_id,
                                             self.date or fields.Date.today())
        else:
            return self.payment_diff_amount_save


class PaymentGroupAdvanceMove(models.Model):
    _name = "payment.group.advance.move"

    move_line_id = fields.Many2one('account.move.line', string='Advance move line', required=True, ondelete='cascade')
    payment_group_id = fields.Many2one('account.payment.group', string='Payment group', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    other_currency_id = fields.Many2one('res.currency', 'Other Currency', readonly=True)
    payment_group_advance_amount = fields.Monetary(currency_field='currency_id')
    pg_advance_amount_currency = fields.Monetary(currency_field='other_currency_id')
    company_id = fields.Many2one(related='payment_group_id.company_id')

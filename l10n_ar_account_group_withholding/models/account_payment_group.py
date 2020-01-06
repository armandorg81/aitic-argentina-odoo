# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import UserError
import datetime
from . import number_to_letter
from odoo.addons import decimal_precision as dp

class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    amount_withholding = fields.Float(string='Withhol. Base.')
    amount_total_payable = fields.Float(string='Total', readonly=True, store=True,
                                        compute='_compute_amount_total_payable')

    withholding_base_amount = fields.Float(string='Withholding Amount', readonly=True, store=True,
                                           compute='_compute_withholding_base_amount', digits=dp.get_precision('Account'))
    withholding_id = fields.Many2one('account.withholding', string='Retencion', domain=[('type_aliquot', '=', 'earnings')])

    total_amount_cancel = fields.Float(string='Total amount canceled')
    is_canceled = fields.Boolean("Canceled", compute='_compute_is_canceled')
    withholding_certificate = fields.Char(string="No.Withholding Certificate", default="Draft Certificate")
    exempt_withholding = fields.Boolean(string="Without withholding", default=False)
    withholding_tax_base = fields.Float(string='Withholding tax base', store=True,
                                        compute='_compute_withholding_tax_base',
                                        inverse='_set_withholding_tax_base',
                                        digits=dp.get_precision('Account'))
    edit_withholding = fields.Boolean(string="Edit withholding tax base", default=False)
    withholding_tax_base_real = fields.Float(string='Withholding tax base',
                                        digits=dp.get_precision('Account'))
    group_invoice_ids = fields.One2many('account.payment.group.invoice', 'group_id', string='Invoice')

    def _convert_payment(self, currency, from_amount, to_currency, company, date, divide=False):
        return currency._convert(from_amount, to_currency, company, date)

    def calculate_base_amount_withholding(self):
        base_amount_withholding = self.amount_payable
        to_pay_move_line_ids = self.to_pay_move_line_ids[0] if self.to_pay_move_line_ids else self.env['account.move.line']
        amount_count = self.amount_payable + (self.to_pay_move_line_ids[0].balance if self.to_pay_move_line_ids else 0.0)
        i = 1
        while amount_count > 0.0 and len(self.to_pay_move_line_ids) > i:
            to_pay_move_line_ids += self.to_pay_move_line_ids[i]
            amount_count += self.to_pay_move_line_ids[i].balance
            i += 1
        no_withholding_amount_iibb = 0.0
        for invoice in self.to_pay_move_line_ids.mapped('invoice_id'):
            if invoice.currency_id != self.currency_id:
                no_withholding_amount_iibb += invoice.currency_id._convert(invoice.no_withholding_amount_iibb,
                                                                           self.currency_id, self.env.user.company_id,
                                                                           invoice.date or fields.Date.today())
            else:
                no_withholding_amount_iibb += invoice.no_withholding_amount_iibb

        residual = 0.0
        for invoice in self.to_pay_move_line_ids.mapped('invoice_id'):
            if invoice.currency_id != self.currency_id:
                residual += invoice.currency_id._convert(invoice.residual,
                                                                           self.currency_id, self.env.user.company_id,
                                                                           invoice.date or fields.Date.today())
            else:
                residual += invoice.residual

        self._update_group_invoice_ids()

        if self.selected_debt < residual:
            subtract = (residual - self.selected_debt)
            #no_withholding_amount_iibb -= subtract
            residual -= subtract

        payment_withholding_amount_iibb = sum((group.withholding_tax_base_real -
                                               sum(x.withholding_tax_real for x in group.group_invoice_ids))
                                              for group in
                                              self.to_pay_move_line_ids.mapped('payment_id.payment_group_id'))

        if payment_withholding_amount_iibb > 0:
            no_withholding_amount_iibb -= payment_withholding_amount_iibb

        if self.invoice_group_ids:
            for inv in self.invoice_group_ids:
                if inv.invoice_id.no_withholding_amount_iibb > inv.advance_amount:
                    no_withholding_amount_iibb -= (inv.invoice_id.no_withholding_amount_iibb - inv.advance_amount)

        if self.amount_payable >= residual and residual > 0:
            base_amount_withholding = no_withholding_amount_iibb + (self.amount_payable - residual)
        # elif self.amount_payable >= no_withholding_amount_iibb:
        #     base_amount_withholding = no_withholding_amount_iibb
        else: #if self.amount_payable < no_withholding_amount_iibb
            base_amount_w = 0
            amount = self.amount_payable + sum(x.amount_residual for x in self.to_pay_move_line_ids.filtered(lambda x: x.payment_id))
            for invoice in self.to_pay_move_line_ids.sorted(key=lambda p: (p.date, p.id)).mapped('invoice_id'):
                if invoice.residual <= amount:
                    amount -= invoice.residual
                    base_amount_w += invoice.no_withholding_amount_iibb
                else:
                    if invoice.no_withholding_amount_iibb > amount:
                        base_amount_w += amount
                    else:
                        base_amount_w += invoice.no_withholding_amount_iibb

            base_amount_w -= payment_withholding_amount_iibb
            base_amount_withholding = base_amount_w

        return base_amount_withholding

    @api.one
    @api.depends('amount_payable', 'to_pay_move_line_ids', 'edit_withholding')
    def _compute_withholding_tax_base(self):
        base_amount_withholding = self.calculate_base_amount_withholding()
        amount_withholding = 0.0
        if not self._context.get('no_update_withholding', False) and not self.is_canceled:
            amount_withholding = base_amount_withholding if self.to_pay_move_line_ids.mapped('invoice_id') and base_amount_withholding <= self.amount_payable else self.amount_payable
        elif self._context.get('no_update_withholding', False) or self.is_canceled:
            amount_withholding = self.withholding_tax_base_real

        self.withholding_tax_base = amount_withholding if amount_withholding >= 0.0 else 0.0

    @api.one
    def _set_withholding_tax_base(self):
        #if self.withholding_tax_base > self.amount_payable:
            #raise UserError(_('The withholding tax base can not be greater than the amount to be paid.'))
        return True

    @api.one
    @api.depends('payment_ids')
    def _compute_is_canceled(self):
        withholdings = self.env['account.withholding'].search([('payment_id', 'in', self.mapped('payment_ids').ids),
                                                               ('state', '=', 'declared')])
        if withholdings:
            self.is_canceled = True
        else:
            self.is_canceled = False


    def _update_group_invoice_ids(self):
        if self.state == 'draft':
            self.group_invoice_ids = self.env['account.payment.group.invoice']
            for invoice in self.to_pay_move_line_ids.mapped('invoice_id'):
                self.group_invoice_ids += self.env['account.payment.group.invoice'].new({
                                                                                        'invoice_id': invoice.id,
                                                                                        'withholding_tax_base': invoice.no_withholding_amount_iibb,
                                                                                    })

    # def _get_is_canceled(self):
    #     payment_withholding = self.mapped('payment_ids').filtered(lambda x:x.is_withholding)
    #     if self.is_canceled or payment_withholding:
    #         return True
    #     else:
    #         return False

    @api.multi
    @api.depends('to_pay_move_line_ids.amount_residual', 'date', 'amount_payable', 'exempt_withholding', 'withholding_tax_base')
    def _compute_withholding_base_amount(self):
        for rec in self:
            if not rec.exempt_withholding:
                if not self._context.get('no_update_withholding') and not rec.is_canceled:
                    rec.withholding_base_amount = rec._do_compute_withholding_amount()
                else:
                    rec.withholding_base_amount = rec._get_amount_earnings_w_pay()

    @api.model
    def _get_default_start_date(self):
        date = fields.Date.from_string(self.date)
        start = datetime.date(date.year, date.month, 1)
        return start


    def _get_previous_amount_withholding(self, is_regimen=False):
        # payments = self.env['account.payment.group'].search([('partner_type', '=', 'supplier'),
        #                                                ('partner_id', '=', self.partner_id.id),
        #                                                ('date', '<=', self.date),
        #                                                ('date', '>=', self._get_default_start_date()),
        #                                                ('state', 'in', ['posted', 'reconciled'])])
        # pay_amount = sum(pay.amount_withholding for pay in payments)
        # withholding_base_amount = sum(pay._get_amount_earnings_w_pay() for pay in payments)
        domain = [('partner_id', '=', self.partner_id.id), ('date', '<=', self.date),
                  ('date', '>=', self._get_default_start_date()), ('type_aliquot', '=', 'earnings')]
        if is_regimen:
            domain.append(('regimen_retencion_id', '=', self.partner_id.regimen_retencion_id.id))
        withholdings = self.env['account.withholding'].search(domain)
        pay_amount = sum(wi.withholding_tax_base_real for wi in withholdings)
        withholding_base_amount = sum(wi.withholding_amount for wi in withholdings)
        domain.append(('active', '=', False))
        withholdings_not_active = self.env['account.withholding'].search(domain)
        pay_amount += sum(wi.withholding_tax_base_real for wi in withholdings_not_active)
        withholding_base_amount += sum(wi.withholding_amount for wi in withholdings_not_active)
        return pay_amount, withholding_base_amount

    def _do_compute_withholding_amount(self):
        diff = 0.0
        if self.env.user.company_id.calculate_wh and self.partner_type == 'supplier'\
                and self.partner_id and self.date and self.amount_payable > 0:
            regimen = self.partner_id.regimen_retencion_id
            if regimen and not self.partner_id.get_exempt_earnings(self.date) and self.withholding_tax_base > 0.0:
                is_regimen = self.env.user.company_id.regime_wh
                pay_amount, withholding_base_amount = self._get_previous_amount_withholding(is_regimen)
                #pay_amount += self.calculate_base_amount_withholding()
                pay_amount += self.withholding_tax_base

                monto_deducible = self.partner_id.inscripto and regimen.montos_no_sujeto or 0.0
                if monto_deducible > 0.0 and pay_amount > monto_deducible:
                    diff = pay_amount - monto_deducible
                    percent = self.partner_id.inscripto and regimen.por_ins or regimen.por_no_ins
                    s_escala = self.partner_id.inscripto and regimen.segun_escala_ins or regimen.segun_escala_nins
                    if not s_escala:
                        diff = diff * (percent / 100)
                    else:
                        scala = self.env['afip.gain.withholding'].search([('amount_from', '<=', diff),
                                                                          ('amount_to', '>=', diff)])
                        if not scala:
                            diff = 0
                        else:
                            diff = diff - scala[0].excess_amount
                            if diff < 0:
                                diff = 0
                            else:
                                diff = diff * (scala[0].rate / 100)
                                diff += scala[0].amount
                    diff -= withholding_base_amount
        return diff if diff > 0.0 else 0.0

    def _get_amount_earnings_w_pay(self):
        self.ensure_one()
        return sum(pay.amount for pay in self.mapped('payment_ids').filtered(lambda x:x.is_withholding and
                                                                                x.type_aliquot == 'earnings'))

    @api.multi
    @api.onchange('to_pay_move_line_ids.amount_residual', 'amount_payable', 'withholding_tax_base')
    def _onchange_amount_withholding(self):
        for rec in self:
            rec.amount_withholding = 0.0
            if rec.partner_type == "supplier":
                if not self._context.get('no_update_withholding'):
                    #rec.amount_withholding = rec.calculate_base_amount_withholding()
                    rec.amount_withholding = rec.withholding_tax_base
                else:
                    # rec.amount_withholding = self._context.get('amount_withholding')
                    rec.amount_withholding = rec._get_amount_w_pay()

    @api.multi
    @api.onchange('to_pay_move_line_ids', 'amount_payable', 'state', 'withholding_base_amount')
    def _onchange_to_pay_amount(self):
        super(AccountPaymentGroup, self)._onchange_to_pay_amount()
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount -= rec.withholding_base_amount

    @api.multi
    @api.depends('amount_payable')
    def _compute_payable_wtax(self):
        super(AccountPaymentGroup, self)._compute_payable_wtax()
        for rec in self:
            rec.amount_payable_wtax += rec.withholding_base_amount

    @api.multi
    @api.depends('amount_payable', 'unreconciled_amount', 'partner_id', 'withholding_base_amount')
    def _compute_to_pay_amount(self):
        super(AccountPaymentGroup, self)._compute_to_pay_amount()
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount -= rec.withholding_base_amount

    @api.multi
    @api.depends('payments_amount', 'withholding_base_amount', 'state')
    def _compute_amount_total_payable(self):
        for rec in self:
            if rec.state == "draft" and not rec.is_canceled:
                rec.amount_total_payable = rec.payments_amount + rec.withholding_base_amount
            else:
                rec.amount_total_payable = rec.payments_amount

    def create_withholding_payments(self):
        if self.withholding_base_amount > 0.0 and not self.mapped('payment_ids').filtered(lambda x: x.is_withholding and x.type_aliquot == 'earnings'):
            journal_id = self.company_id.supplier_wh_journal_id
            if not journal_id:
                raise UserError(_('You must comfigurate in the company the withholding journal.'))
            payment_method_id = self.env.ref('account.account_payment_method_manual_out', False)
            currency = self.currency_id
            withholding_base_amount = self.withholding_base_amount
            currency_journal = journal_id.currency_id or journal_id.company_id.currency_id
            if currency_journal and currency_journal != currency:
                # withholding_base_amount = currency._convert(self.withholding_base_amount, currency_journal,
                #                                             self.env.user.company_id,
                #                                             self.date or fields.Date.today())
                withholding_base_amount = self._convert_payment(currency, self.withholding_base_amount, currency_journal,
                                                                self.env.user.company_id, self.date or fields.Date.today())

                currency = currency_journal
            vals = {
                'journal_id': journal_id.id,
                'payment_method_id': payment_method_id.id,
                'payment_date': self.date,
                'payment_type': 'outbound',
                'currency_id': currency.id,
                'communication': _("Withholding Earnings"),
                'partner_id': self.partner_id.id,
                'partner_type': self.partner_type,
                'payment_group_company_id': self.company_id.id,
                # 'payment_group': True,
                'amount': withholding_base_amount,
                'amount_aliquot_in_words': number_to_letter.to_word_no_decimal(withholding_base_amount),
                'name': '',
                'is_withholding': True,
                'type_aliquot': 'earnings',
                'state': 'draft'}

            self.payment_ids += self.env['account.payment'].create(vals)

    def _get_amount_w_pay(self):
        self.ensure_one()
        return sum(pay.amount for pay in self.mapped('payment_ids').filtered(lambda x:x.is_withholding and
                                                                                x.type_aliquot == 'earnings'))

    def _get_is_aliquot(self):
        return False

    def generate_withholding_payments(self):
        for rec in self:
            if rec.partner_type == "supplier":
                if not rec.is_canceled:
                    rec.create_withholding_payments()
                    is_certificate = rec._get_is_aliquot()
                    if is_certificate:
                        rec.withholding_certificate = self.env['ir.sequence'].next_by_code('withholding.certificate')
                else:
                    amount_total = 0.0
                    for pay in rec.payment_ids:
                        if pay.currency_id != rec.currency_id:
                            # amount_total += pay.currency_id._convert(pay.amount, rec.currency_id, rec.env.user.company_id,
                            #                                    rec.date or fields.Date.today())
                            amount_total += pay._convert_payment(pay.currency_id, pay.amount,
                                                                 rec.currency_id, rec.env.user.company_id,
                                                                 rec.date or fields.Date.today())
                    # amount_total = sum(pay.amount for pay in rec.payment_ids)
                    if amount_total > rec.total_amount_cancel:
                        raise UserError(_('The amount to be paid must not be greater than the amount initially paid.'))

            rec.withholding_tax_base_real = rec.withholding_tax_base
        ctx = dict(self._context)
        ctx.update({'no_update_withholding': True,
                    'amount_withholding': self.amount_withholding,
                    'withholding_base_amount': self.withholding_base_amount})
        res = super(AccountPaymentGroup, self.with_context(ctx)).generate_withholding_payments()
        return res

    def create_withholding(self):
        res = super(AccountPaymentGroup, self).create_withholding()
        for rec in self:
            # rec.is_canceled = False
            rec.to_pay_move_line_ids.mapped('payment_id.payment_group_id').update_payment_down()
            rec._post_update_group_invoice_ids()

            if rec.withholding_base_amount > 0.0 and rec.company_id.calculate_wh:
                payment = rec.mapped('payment_ids').filtered(lambda x: x.is_withholding and
                                                                        x.type_aliquot == 'earnings')
                if payment:
                    if not rec.withholding_id:
                        sequence = rec.env['ir.sequence'].with_context(ir_sequence_date=payment.payment_date).next_by_code(
                            'account.withholding')
                        withholding = rec.env['account.withholding'].create({'name': sequence,
                                                                             'withholding_amount': payment.amount,
                                                                             'date': rec.date,
                                                                             'partner_id': rec.partner_id.id,
                                                                             'regimen_retencion_id': rec.partner_id.regimen_retencion_id.id,
                                                                             'invoice_ids': [(4, invoice.id, None) for
                                                                                             invoice in rec.invoice_ids],
                                                                             'reference': rec.name,
                                                                             'payment_id': payment[0].id,
                                                                             'state': 'done',
                                                                             'withholding_tax_base_real': rec.withholding_tax_base_real,
                                                                             'type_aliquot': 'earnings'})
                        rec.withholding_id = withholding.id
                    elif payment and rec.withholding_id:
                        rec.withholding_id.write({
                            'withholding_amount': payment.amount,
                            'date': rec.date,
                            'partner_id': rec.partner_id.id,
                            # 'regimen_retencion_id': rec.partner_id.regimen_retencion_id.id,
                            'invoice_ids': [(5, 0, 0)] + [(4, invoice.id, None) for invoice in rec.invoice_ids],
                            'reference': rec.name,
                            'payment_id': payment[0].id,
                            'state': 'done' if rec.withholding_id.state != 'declared' else 'declared',
                            'withholding_tax_base_real': rec.withholding_tax_base_real,
                        })
            elif rec.env.user.company_id.calculate_wh and rec.partner_type == 'supplier' and rec.amount_payable > 0:
                regimen = rec.partner_id.regimen_retencion_id
                if regimen and not rec.partner_id.get_exempt_earnings(rec.date) and rec.withholding_tax_base > 0.0:
                    withholding = rec.env['account.withholding'].create({'name': 'Withholding 0.0',
                                                                         'withholding_amount': rec.withholding_base_amount,
                                                                         'date': rec.date,
                                                                         'partner_id': rec.partner_id.id,
                                                                         'regimen_retencion_id': rec.partner_id.regimen_retencion_id.id,
                                                                         'invoice_ids': [(4, invoice.id, None) for
                                                                                         invoice in rec.invoice_ids],
                                                                         'reference': rec.name,
                                                                         'payment_id': rec.mapped('payment_ids')[0].id,
                                                                         'state': 'done',
                                                                         'withholding_tax_base_real': rec.withholding_tax_base_real,
                                                                         'type_aliquot': 'earnings',
                                                                         'active': False})
        return res

    def _post_update_group_invoice_ids(self):
        withholding_tax_real_total = self.withholding_tax_base_real
        for line in self.with_context({'payment_group_id': self.id,
                                       'matched_lines': True}).matched_move_line_ids.filtered(lambda x:
                                        x.invoice_id).sorted(key=lambda i: i.amount_residual_currency, reverse=True):
            group_invoice = self.group_invoice_ids.filtered(lambda x: x.invoice_id == line.invoice_id)
            if group_invoice and withholding_tax_real_total > 0.0:
                if withholding_tax_real_total > group_invoice[0].withholding_tax_base:
                    withholding_tax_real = group_invoice[0].withholding_tax_base
                else:
                    withholding_tax_real = withholding_tax_real_total
                withholding_tax_real_total -= withholding_tax_real
                group_invoice[0].write({
                    'withholding_tax_real': withholding_tax_real
                })

    def update_payment_down(self):
        for rec in self:
            withholding_tax_real_total = rec.withholding_tax_base_real - sum(x.withholding_tax_real for x in rec.group_invoice_ids)
            for move in rec.matched_move_line_ids.with_context(payment_group_id=rec.id).sorted(key=lambda p: (p.date, p.id)):
                if move.invoice_id and not rec.group_invoice_ids.filtered(lambda x: x.invoice_id == move.invoice_id):
                    if withholding_tax_real_total > 0:
                        withholding_tax_real = withholding_tax_real_total if withholding_tax_real_total <  move.invoice_id.no_withholding_amount_iibb else move.invoice_id.no_withholding_amount_iibb
                        self.env['account.payment.group.invoice'].create({
                            'invoice_id': move.invoice_id.id,
                            'group_id': rec.id,
                            'withholding_tax_base': move.invoice_id.no_withholding_amount_iibb,
                            'withholding_tax_real': withholding_tax_real,
                        })
                        withholding_tax_real_total -= withholding_tax_real


    def _create_group_invoice_ids(self, invoice):
        withholding_tax_real_total = self.withholding_tax_base_real
        withholding_tax_real_sum = sum(x.withholding_tax_real for x in self.group_invoice_ids)
        withholding_tax_real = withholding_tax_real_total - withholding_tax_real_sum
        if withholding_tax_real > invoice.no_withholding_amount_iibb:
            withholding_tax_real = invoice.no_withholding_amount_iibb
        self.env['account.payment.group.invoice'].create({
            'invoice_id': invoice.id,
            'group_id': self.id,
            'withholding_tax_base': invoice.no_withholding_amount_iibb,
            'withholding_tax_real': withholding_tax_real,
        })

    @api.multi
    def cancel(self):
        for rec in self:
            rec.write({
                # 'is_canceled': True,
                'total_amount_cancel': rec.amount_payable
            })

            rec._compute_to_pay_amount()

            super(AccountPaymentGroup, rec.with_context({'no_update_withholding': True,
                                                         'amount_withholding': rec.amount_withholding,
                                                         'withholding_tax_base': rec.withholding_tax_base,
                                                         })).cancel()
            rec.payment_ids.write({'move_name': False})
            if rec.withholding_id and rec.withholding_id.state == 'done':
                rec.withholding_id.action_annulled()
            withholding_ids = self.env['account.withholding'].search([('active', '=', False)]).filtered(lambda x: x.payment_group_id == rec)
            if withholding_ids:
                withholding_ids.unlink()
        return True

    @api.multi
    def write(self, vals):
        for rec in self:
            if not 'state' in vals:
                vals['state'] = self.state
        return super(AccountPaymentGroup, self).write(vals)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.withholding_id and rec.withholding_id.state == 'declared':
                raise UserError(_(
                    "You cannot delete a payment with declared withholdings."))
            elif rec.withholding_id:
                rec.withholding_id.unlink()
        return super(AccountPaymentGroup, self).unlink()

    @api.one
    def get_withholding_receipt(self):
        if self.payment_ids.filtered(lambda x: x.customers_withholding):
            return True
        else:
            return False
        return super(AccountPaymentGroup, self).unlink()

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        value = False
        if self._name == 'account.payment.group':
            a = []
            value = False
            for do in domain:
                if do[0] == 'payment_ids':
                    value = do[2]
                    domain.remove(do)
        records = self.search(domain or [], offset=offset, limit=limit, order=order)
        if value:
            if self._context.get('journal_search', False):
                payms = self.env['account.payment'].search([('journal_id', 'ilike', value)])
                records = records.mapped('payment_ids').filtered(lambda x: x in payms).mapped('payment_group_id')
            else:
                if records[0].partner_type == 'customer':
                    payms = self.env['account.payment'].search([('withholding_receipt', 'ilike', value)])
                    records = records.mapped('payment_ids').filtered(lambda x: x in payms).mapped('payment_group_id')
                else:
                    withholding = self.env['account.withholding'].search([('name', 'ilike', value)])
                    records = records.filtered(lambda x: x.withholding_id in withholding)

        if not records:
            return []

        if fields and fields == ['id']:
            return [{'id': record.id} for record in records]

        # TODO: Move this to read() directly?
        if 'active_test' in self._context:
            context = dict(self._context)
            del context['active_test']
            records = records.with_context(context)

        result = records.read(fields)
        if len(result) <= 1:
            return result

        index = {vals['id']: vals for vals in result}
        return [index[record.id] for record in records if record.id in index]

class AccountPaymentGroupInvoice(models.Model):
    _name = "account.payment.group.invoice"

    invoice_id = fields.Many2one('account.invoice', string='Invoice')
    withholding_tax_base = fields.Float(string='withholding tax base',
                                             digits=dp.get_precision('Account'), default=0.0)
    withholding_tax_real = fields.Float(string='withholding tax base',
                                             digits=dp.get_precision('Account'), default=0.0)
    group_id = fields.Many2one('account.payment.group', string='Group', ondelete='cascade')



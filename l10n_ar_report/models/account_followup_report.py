# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from datetime import datetime
from odoo.tools.misc import formatLang, format_date


class ReportAccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"

    def get_lines(self, options, line_id=None):
        # Get date format for the lang
        partner = options.get('partner_id') and self.env['res.partner'].browse(options['partner_id']) or False
        if not partner:
            return []
        lang_code = partner.lang or self.env.user.lang or 'en_US'

        lines = []
        res = {}
        today = datetime.today().strftime('%Y-%m-%d')
        line_num = 0
        for l in partner.unreconciled_aml_ids:
            if self.env.context.get('print_mode') and l.blocked:
                continue
            currency = l.currency_id or l.company_id.currency_id
            if currency not in res:
                res[currency] = []
            res[currency].append(l)
        for currency, aml_recs in res.items():
            total = 0
            total_issued = 0
            aml_recs = sorted(aml_recs, key=lambda aml: aml.blocked)
            for aml in aml_recs:
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                date_due = format_date(self.env, aml.date_maturity or aml.date, lang_code=lang_code)
                total += not aml.blocked and amount or 0
                is_overdue = today > aml.date_maturity if aml.date_maturity else today > aml.date
                is_payment = aml.payment_id
                if is_overdue or is_payment:
                    total_issued += not aml.blocked and amount or 0
                if is_overdue:
                    date_due = {'name': date_due, 'class': 'color-red date', 'style': 'white-space:nowrap;text-align:center;color: red;'}
                if is_payment:
                    date_due = ''
                move_line_name = aml.move_id.name
                if aml.invoice_id and aml.invoice_id.num_comprobante:
                    move_line_name += ' ('+aml.invoice_id.num_comprobante.zfill(8)+')'
                if self.env.context.get('print_mode'):
                    move_line_name = {'name': move_line_name, 'style': 'text-align:right; white-space:normal;'}
                amount = formatLang(self.env, amount, currency_obj=currency)
                line_num += 1
                columns = [format_date(self.env, aml.date, lang_code=lang_code), date_due, move_line_name, aml.expected_pay_date and aml.expected_pay_date +' '+ aml.internal_note or '', {'name': aml.blocked, 'blocked': aml.blocked}, amount]
                if self.env.context.get('print_mode'):
                    columns = columns[:3]+columns[5:]
                lines.append({
                    'id': aml.id,
                    'name': move_line_name,
                    'caret_options': 'followup',
                    'move_id': aml.move_id.id,
                    'type': is_payment and 'payment' or 'unreconciled_aml',
                    'unfoldable': False,
                    'has_invoice': bool(aml.invoice_id),
                    'columns': [type(v) == dict and v or {'name': v} for v in columns],
                })
            totalXXX = formatLang(self.env, total, currency_obj=currency)
            line_num += 1
            lines.append({
                'id': line_num,
                'name': '',
                'class': 'total',
                'unfoldable': False,
                'level': 0,
                'columns': [{'name': v} for v in ['']*(2 if self.env.context.get('print_mode') else 4) + [total >= 0 and _('Total Due') or '', totalXXX]],
            })
            if total_issued > 0:
                total_issued = formatLang(self.env, total_issued, currency_obj=currency)
                line_num += 1
                lines.append({
                    'id': line_num,
                    'name': '',
                    'class': 'total',
                    'unfoldable': False,
                    'level': 0,
                    'columns': [{'name': v} for v in ['']*(2 if self.env.context.get('print_mode') else 4) + [_('Total Overdue'), total_issued]],
                })
        return lines

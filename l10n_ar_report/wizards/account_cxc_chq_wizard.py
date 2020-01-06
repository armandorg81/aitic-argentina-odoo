# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import datetime
import calendar
import base64
import re
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class account_cxc_chq_wizard(models.TransientModel):
    _name = 'account.cxc.chq.wizard'
    _description = 'Summary of composition of sales balances'

    date = fields.Date(
        'Date', default=fields.Date.context_today)

    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.user.company_id,
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Partner',
        domain=[('customer', '=', True)]
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Partner',
        domain=[('supplier', '=', True)]
    )
    days_check_endorsed = fields.Integer(
        'Days of old endorsed checks', default=30
    )
    days_check_deposited = fields.Integer(
        'Days of old deposited checks', default=5
    )
    type = fields.Selection([
                    ('sale','Sale'),
                    ('purchase','Purchase')],
                    string="Type")

    def print_report(self):
        data = {'ids': self.env.context.get('active_ids', [])}
        res = self.read()
        res = res and res[0] or {}
        data.update({'form': res})
        if self.type == 'sale':
            res = self.read(['date', 'company_id', 'days_check_endorsed','days_check_deposited', 'customer_id'])
            res = res and res[0] or {}
            data.update({'form': res})
            return self.env.ref('l10n_ar_report.report_account_cxc_chq').report_action([], data=data)
            # return self.env['report'].get_action(self,'l10n_ar_report.report_account_cxc_check', data=data)
        else:
            res = self.read(['date', 'company_id', 'days_check_endorsed','days_check_deposited', 'supplier_id'])
            res = res and res[0] or {}
            data.update({'form': res})
            return self.env.ref('l10n_ar_report.report_account_cxp_chq').report_action([], data=data)
            # return self.env['report'].get_action(self,'l10n_ar_report.report_account_cxp_check', data=data)

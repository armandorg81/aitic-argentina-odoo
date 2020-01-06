# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, api, tools, models, _
from odoo.exceptions import UserError, Warning, RedirectWarning, ValidationError
from itertools import groupby
from dateutil.relativedelta import relativedelta
from datetime import datetime

class AcountCXPCheck(models.AbstractModel):
    _name = 'report.l10n_ar_report.report_account_cxp_check'
    _description = "Resumen de Composicion de Saldos de Compra"
    
    #def render_html(self, ids, data=None, context=None):
    @api.model
    def _get_report_values(self, docids, data=None):
        supplier_id = False
        if not data and docids:
            data = self.env['account.cxc.chq.wizard'].browse(docids)
            company_id = data['company_id'][0].id
            if data['supplier_id']:
                supplier_id = data['supplier_id'][0].id
        else:
            data = data['form']
            company_id = data['company_id'][0]
            if data['supplier_id']:
                supplier_id = data['supplier_id'][0]
        date = data['date']
        days_check_endorsed = data['days_check_endorsed']
        days_check_deposited = data['days_check_deposited']
        partner_obj = self.env['res.partner']
        invoice_obj = self.env['account.invoice']
        check_obj = self.env['account.check']
        aux_obj = self.env['aux.report.account.cxc.chq']
        if supplier_id:
            partners = partner_obj.search([('supplier', '=', True),('id', '=', supplier_id)])
        else:
            check = check_obj.search([('type', '=', 'third_check'),
                                      ('company_id', '>=', company_id)])
            partners = check.mapped('partner_id').filtered(lambda x: x.supplier)
            # partners = partner_obj.search([('supplier', '=', True)])

        aux_obj.search([]).unlink()
        list_detail = []
        for partner in partners:
            details = {}
            invoices = invoice_obj.search([
                    ('state', 'in', ['open']),
                    ('partner_id', '=', partner.id),
                    ('company_id', '=', company_id),
                    ('date_invoice', '<=', date),
                    ('type', 'in', ('in_invoice', 'in_refund'))
                    ])

            amount_invoice = sum(line.residual_signed for line in invoices)

            check = check_obj.search([('type', '=', 'third_check'),
                                      ('state', '=', 'delivered'),
                                      ('company_id', '>=', company_id)]).filtered(lambda x:
                                                                              x.operation_partner_id.id == partner.id)

            date_delivered = datetime.strptime(date, '%Y-%m-%d') + relativedelta(days=(days_check_endorsed*-1))
            amount_check_delivered = sum(line.amount for line in check.filtered(lambda x: x.payment_date.strftime("%Y-%m-%d") >= date_delivered.strftime("%Y-%m-%d")))

            if amount_invoice != 0.00 or amount_check_delivered != 0.00:
                detail = {
                    'partner_id': partner.id,
                    'company_id': company_id,
                    'amount_invoice': amount_invoice,
                    'amount_check_hand': 0.0,
                    'amount_check_delivered': amount_check_delivered,
                    'amount_subtotal': 0.0,
                    'amount_check_deposited': 0.0,
                    'amount_total': amount_invoice + amount_check_delivered,
                }
                list_detail.append((0, 0, detail))
        aux = {
            'company_id': company_id,
            'date': (datetime.strptime(date, '%Y-%m-%d')).strftime("%Y-%m-%d"),
            'days_check_endorsed': days_check_endorsed,
            'days_check_deposited': 0,
            'detail_ids': list_detail,
        }

        aux_id = aux_obj.create(aux)
        report = self.env['ir.actions.report']._get_report_from_name('l10n_ar_report.report_account_cxp_check')
        return {
            'doc_ids': [aux_id.id],
            'doc_model': report.model,
            'data': data,
            'docs': aux_id,
        }


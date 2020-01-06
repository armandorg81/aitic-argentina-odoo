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

class AcountCXCCheck(models.AbstractModel):
    _name = 'report.l10n_ar_report.report_account_cxc_check'
    _description = "Resumen de Composicion de Saldos de Venta"
    
    #def render_html(self, ids, data=None, context=None):
    @api.model
    def _get_report_values(self, docids, data=None):
        customer_id = False
        if not data and docids:
            data = self.env['account.cxc.chq.wizard'].browse(docids)
            company_id = data['company_id'][0].id
            if data['customer_id']:
                customer_id = data['customer_id'][0].id
        else:
            data = data['form']
            company_id = data['company_id'][0]
            if data['customer_id']:
                customer_id = data['customer_id'][0]
        date = data['date']
        days_check_endorsed = data['days_check_endorsed']
        days_check_deposited = data['days_check_deposited']
        partner_obj = self.env['res.partner']
        invoice_obj = self.env['account.invoice']
        check_obj = self.env['account.check']
        aux_obj = self.env['aux.report.account.cxc.chq']
        if customer_id:
            partners = partner_obj.search([('customer', '=', True), ('id', '=', customer_id)])
        else:
            check = check_obj.search([('type', '=', 'third_check'),
                                      ('company_id', '>=', company_id)])
            partners = check.mapped('partner_id').filtered(lambda x: x.customer)
                # partner_obj.search([('customer', '=', True)])
        aux_obj.search([]).unlink()
        list_detail = []
        for partner in partners:
            details = {}
            invoices = invoice_obj.search([
                    ('state', 'in', ['open']),
                    ('partner_id', '=', partner.id),
                    ('company_id', '=', company_id),
                    ('date_invoice', '<=', date),
                    ('type', 'in', ('out_invoice', 'out_refund'))
                    ])

            amount_invoice = sum(line.residual_signed for line in invoices)

            check = check_obj.search([('type', '=', 'third_check'),
                                      ('company_id', '>=', company_id)]).filtered(lambda x:
                                                                              x.partner_id.id == partner.id)

            amount_check_hand = sum(line.amount for line in check.filtered(lambda x: x.state =='holding'))

            date_delivered = datetime.strptime(date, '%Y-%m-%d') + relativedelta(days=(days_check_endorsed*-1))
            amount_check_delivered = sum(line.amount for line in check.filtered(lambda x:
                                                                                    x.state =='delivered' and
                                                                                    x.payment_date.strftime("%Y-%m-%d") >= date_delivered.strftime("%Y-%m-%d")))

            date_deposited = datetime.strptime(date, '%Y-%m-%d') + relativedelta(days=(days_check_deposited*-1))
            amount_check_deposited = sum(line.amount for line in check.filtered(lambda x:
                                                                                    x.state =='deposited' and
                                                                                    x.deposited_date.strftime("%Y-%m-%d") >= date_deposited.strftime("%Y-%m-%d")
                                                                                    and x.deposited_date.strftime("%Y-%m-%d") <= date))
            if amount_invoice != 0.00 or amount_check_hand != 0.00 or amount_check_delivered != 0.00 or \
                amount_check_deposited != 0.00:
                detail = {
                    'partner_id': partner.id,
                    'company_id': company_id,
                    'amount_invoice': amount_invoice,
                    'amount_check_hand': amount_check_hand,
                    'amount_check_delivered': amount_check_delivered,
                    'amount_subtotal': amount_invoice + amount_check_hand + amount_check_delivered,
                    'amount_check_deposited': amount_check_deposited,
                    'amount_total': amount_invoice + amount_check_hand + amount_check_delivered + amount_check_deposited,
                }
                list_detail.append((0, 0, detail))
        aux = {
            'company_id': company_id,
            'date': (datetime.strptime(date, '%Y-%m-%d')).strftime("%Y-%m-%d"),
            'days_check_endorsed': days_check_endorsed,
            'days_check_deposited': days_check_deposited,
            'detail_ids': list_detail,
        }

        aux_id = aux_obj.create(aux)
        report = self.env['ir.actions.report']._get_report_from_name('l10n_ar_report.report_account_cxc_check')
        return {
            'doc_ids': [aux_id.id],
            'doc_model': report.model,
            'data': data,
            'docs': aux_id,
        }
    
class aux_report_commission(models.TransientModel):
    _name = "aux.report.account.cxc.chq"
    _description = "Auxiliar"

    company_id = fields.Many2one('res.company', 'Company')
    detail_ids = fields.One2many('aux.report.account.cxc.chq.details', 'aux_id', 'Child')
    date = fields.Char('Date')
    days_check_endorsed = fields.Integer(
        'Days of old endorsed checks',
    )
    days_check_deposited = fields.Integer(
        'Days of old deposited checks',
    )

class aux_report_commission(models.TransientModel):
    _name = "aux.report.account.cxc.chq.details"
    _description = "Auxiliar"

    partner_id = fields.Many2one('res.partner', 'Partner')
    company_id = fields.Many2one('res.company', 'Company')
    amount_invoice = fields.Float(string='Amount of invoices')
    amount_check_hand = fields.Float(string='Amount of check in hand')
    amount_check_delivered = fields.Float(string='Amount of delivered checks')
    amount_check_deposited = fields.Float(string='Amount of deposited checks')
    amount_subtotal = fields.Float(string='Subtotal')
    amount_total = fields.Float(string='total')
    aux_id = fields.Many2one('aux.report.account.cxc.chq', 'Parent')


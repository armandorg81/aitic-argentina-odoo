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
import operator


class account_aliquot_agip_wizard(models.TransientModel):
    _name = 'account.aliquot.agip.wizard'
    _description = 'Aliquot AGIP Export'


    from_date = fields.Date('From', default=datetime.datetime.now().strftime('%Y-%m-01'))

    to_date = fields.Date('To', default=(datetime.datetime.now() + \
                                         relativedelta(months=+1, day=1, days=-1)).strftime('%Y-%m-%d'))

    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env['res.company'].search([('parent_id', '=', False)], order='id', limit=1),
        required=True)

    activity = fields.Selection([
        ('pw', 'Perception/withholding'),
        ('pcn', 'Perception credit notes')],
        string='Activities', required=True, default='pw')

    txt_filename = fields.Char()
    txt_binary = fields.Binary()
    is_data = fields.Boolean('Is data')
    mark_declared = fields.Boolean('Declared withholding', help='Mark withholding as declared', default=False)


    @api.multi
    def confirm(self):
        self.ensure_one()

        # build txt filename
        if self.activity == "pw":
            txt_filename = "IBPercRetEmitida_CAPITAL_FEDERAL"
        else:
            txt_filename = "IBPercEmitidaCR_CAPITAL_FEDERAL"

        # build txt file
        content = ''
        if self.activity == "pw":
            content = self.get_content(self.from_date, self.to_date, self.mark_declared)
        else:
            content = self.get_content_pcn(self.from_date, self.to_date)

        # save file
        bytes_base64_encoded = base64.encodebytes(content.encode('utf-8'))
        is_data = content != '' and True or False
        self.write({
            'txt_filename': '%s.txt' % (txt_filename),
            'txt_binary': bytes_base64_encoded.decode('utf-8').replace('\n', ''),
            'is_data': is_data
        })
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'res_model': 'account.aliquot.agip.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref(
                'l10n_ar_perception_withholding_agip.account_aliquot_agip_wizard_download').id,
            'context': self.env.context,
            'target': 'new',
        }

    def get_content(self, from_date, to_date, mark_declared):
        invoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', from_date),
                                                     ('date_invoice', '<=', to_date),
                                                     ('state', 'in', ['open','paid']),
                                                     ('tipo_comprobante.type', '!=', 'credit_note')])
        content = ''
        vals = {}
        for invoice in invoice_ids.sorted(key='date_invoice'):
            tax_lines = invoice.tax_line_ids.filtered(lambda x: x.tax_id.is_perception == True and
                                                                x.tax_id.type_aliquot == 'agip')
            if tax_lines:
                base = sum(line.base for line in tax_lines)
                if invoice.currency_id != invoice.company_id.currency_id:
                    amount_total = invoice._convert_invoice(invoice.currency_id, invoice.amount_total, invoice.company_id.currency_id,
                                                            invoice.company_id,
                                                            invoice._get_currency_rate_date() or fields.Date.today())
                    amount_other = invoice._convert_invoice(invoice.currency_id,
                                                            (invoice.amount_total - invoice.amount_iva - invoice.neto_gravado),
                                                            invoice.company_id.currency_id, invoice.company_id,
                                                            invoice._get_currency_rate_date() or fields.Date.today())

                    amount_iva = invoice._convert_invoice(invoice.currency_id, invoice.amount_iva, invoice.company_id.currency_id,
                                                            invoice.company_id,
                                                            invoice._get_currency_rate_date() or fields.Date.today())
                    amount_untaxed = invoice._convert_invoice(invoice.currency_id, (base != 0.0 and base or invoice.neto_gravado),
                                                              invoice.company_id.currency_id, invoice.company_id,
                                                              invoice._get_currency_rate_date() or fields.Date.today())

                    amount = invoice._convert_invoice(invoice.currency_id, sum(line.amount for line in tax_lines),
                                                      invoice.company_id.currency_id, invoice.company_id,
                                                      invoice._get_currency_rate_date() or fields.Date.today())
                else:
                    amount_total = invoice.amount_total
                    amount_other = invoice.amount_total - invoice.amount_iva - invoice.neto_gravado
                    amount_iva = invoice.amount_iva
                    amount_untaxed = base != 0.0 and base or invoice.neto_gravado
                    amount = sum(line.amount for line in tax_lines)
                cuit = invoice.partner_id.cuit.replace('-','')
                iibb_type = self._get_iibb_type(invoice.partner_id)
                acceptance = ' '
                date_acceptance = " ".ljust(10, " ")
                vals_invoice = {
                    'type_o': "2",
                    'code': self.company_id.code_perception or '',
                    'date': invoice.date_invoice,
                    'voucher_type': '01' if not invoice.tipo_comprobante.comprobante_credito else '10',
                    'voucher_letter': invoice.tipo_comprobante.desc,
                    'branch_office': invoice.punto_venta.name,
                    'voucher_number': invoice.num_comprobante,
                    'amount_total': amount_total,
                    'certificate': '',
                    'document_type': self._get_document_type(invoice.partner_id),
                    'cuit': cuit,
                    'iibb_type': iibb_type,
                    'iibb_code': (iibb_type == '2' and cuit or invoice.partner_id.ingresos_brutos) or '',
                    'responsability_type': self._get_responsability_type(invoice.partner_id),
                    'name': self._get_partner_name(invoice.partner_id),
                    'amount_other': amount_other,
                    'amount_iva': amount_iva,
                    'amount_untaxed': amount_untaxed,
                    'aliquot': tax_lines[0].tax_id.amount,
                    'amount': amount,
                    'acceptance': acceptance,
                    'date_acceptance': date_acceptance,
                }

                if vals.get(invoice.date_invoice, False):
                    vals[invoice.date_invoice].append(vals_invoice)
                else:
                    vals[invoice.date_invoice] = [vals_invoice]

        group_ids = self.env['account.payment.group'].search([('date', '>=', from_date),
                                                              ('date', '<=', to_date),
                                                              ('state', 'in', ['confirmed', 'posted'])])
        withholding_ids = self.env['account.withholding']
        for group in group_ids:
            if group.amount_agip_withholding != 0.0:
                if group.currency_id != group.company_id.currency_id:
                    amount_total = group._convert_payment(group.currency_id, group.amount_total_payable,
                                                            group.company_id.currency_id,
                                                            group.company_id,
                                                            group.date or fields.Date.today())
                    amount_untaxed = group._convert_payment(group.currency_id,group.amount_withholding,
                                                              group.company_id.currency_id, group.company_id,
                                                            group.date or fields.Date.today())
                else:
                    amount_total = group.amount_total_payable
                    amount_untaxed = group.amount_withholding
                amount_other = amount_total - amount_untaxed
                amount = group.payment_ids.filtered(lambda x: x.is_withholding == True and x.type_aliquot == 'agip').amount
                # for line in group.payment_ids.filtered(lambda x: x.is_withholding == False):
                #     if line.currency_id != group.company_id.currency_id:
                #         amount_other -= line._convert_payment(line.currency_id, line.amount,
                #                                       group.company_id.currency_id, group.company_id,
                #                                     group.date or fields.Date.today())
                #     else:
                #         amount_other -= line.amount
                cuit = group.partner_id.cuit.replace('-', '')
                iibb_type = self._get_iibb_type(group.partner_id)
                acceptance = ' '
                if group.withholding_agip_id.acceptance == 'express':
                    acceptance = 'E'
                elif group.withholding_agip_id.acceptance == 'tacit':
                    acceptance = 'T'
                date_acceptance = " ".ljust(10, " ")
                if group.withholding_agip_id.acceptance == 'express':
                    date_acceptance = fields.Date.from_string(group.withholding_agip_id.date_acceptance).strftime('%d/%m/%Y')
                vals_payment = {
                    'type_o': "1",
                    'code': self.company_id.code_withholding or '',
                    'date': group.date,
                    'voucher_type': '03',
                    'voucher_letter': ' ',
                    'branch_office': self.company_id.branch_number,
                    'voucher_number': group.name,
                    'amount_total': amount_total,
                    'certificate': self.company_id.branch_number.zfill(4) + fields.Date.from_string(
                                    group.date).strftime('%Y') + group.withholding_certificate.zfill(8),
                    'document_type': self._get_document_type(group.partner_id),
                    'cuit': cuit,
                    'iibb_type': iibb_type,
                    'iibb_code': (iibb_type == '2' and cuit or group.partner_id.ingresos_brutos) or '',
                    'responsability_type': self._get_responsability_type(group.partner_id),
                    'name': self._get_partner_name(group.partner_id),
                    'amount_other': amount_other,
                    'amount_iva': 0.0,
                    'amount_untaxed': amount_untaxed,
                    'aliquot': group.withholding_agip_id.withholding_agip_aliquot if group.withholding_agip_id else 0.0,
                    'amount': amount,
                    'acceptance': acceptance,
                    'date_acceptance': date_acceptance,
                }

                if vals.get(group.date, False):
                    vals[group.date].append(vals_payment)
                else:
                    vals[group.date] = [vals_payment]
                withholding_ids += group.withholding_agip_id

        if mark_declared:
            withholding_ids.action_declared()

        for key, values in sorted(vals.items(), key=operator.itemgetter(0)):
            for value in values:
                # Tipo de Operacion [1]
                content += value['type_o']
                # Codigo de Norma [3]
                content += value['code'].zfill(3)
                # Fecha Retencion/Percepcion      [10] (dd/mm/yyyy)
                content += fields.Date.from_string(value['date']).strftime('%d/%m/%Y')
                # Tipo de comprobante      [2]
                content += value['voucher_type'].zfill(2)
                # Letra del Comprobante      [1]
                content += value['voucher_letter']
                # Nro de comprobante compuesto por el Nro Sucursal y Nro emision [16]
                # Numero de sucursal            [5]
                content += value['branch_office'].zfill(5)
                # Numero Emision            [11]
                content += (value['voucher_number'] or "").zfill(11)
                # Fecha Emision Comprobante      [10] (dd/mm/yyyy)
                content += fields.Date.from_string(value['date']).strftime('%d/%m/%Y')
                # Monto del comprobante            [16]
                content += ('%016.2f' % (value['amount_total'])).replace('.', ',')
                # Nro de certificado propio           [16]
                content += value['certificate'].ljust(16, " ")
                # Tipo de documento del Retenido      [1]
                content += value['document_type']
                # Cuit contribuyente Percibido [11]
                content += value['cuit'].zfill(11)
                # Situacion IB del Retenido       [1]
                content += value['iibb_type']
                # Nro Inscripción IB del Retenido  [11]
                content += value['iibb_code'].zfill(11)
                # Situacion frente al IVA del Retenido       [1]
                content += value['responsability_type']
                # Razón Social del Retenido           [30]
                content += value['name'].ljust(30, " ")[0:30]
                # Importe otros conceptos            [16]
                content += ('%016.2f' % (value['amount_other'])).replace('.', ',')
                # Importe IVA            [16]
                content += ('%016.2f' % (value['amount_iva'])).replace('.', ',')
                # Monto Sujeto a Retencion/ Percepcion            [16]
                content += ('%016.2f' % (value['amount_untaxed'])).replace('.', ',')
                # Alícuota           [5]
                content += ('%05.2f' % (value['aliquot'])).replace('.', ',')
                # Retencion/Percepcion Practicada            [16]
                content += ('%016.2f' % (value['amount'])).replace('.', ',')
                # Monto Total Retenido/Percibido            [16]
                content += ('%016.2f' % (value['amount'])).replace('.', ',')
                # Aceptación           [1]
                content +=  " ".ljust(1, " ")
                #Fecha Aceptación "Expresa"           [10]
                content +=  " ".ljust(10, " ")
                content += '\r\n'

        return content

    def get_content_pcn(self, from_date, to_date):
        invoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', from_date),
                                                     ('date_invoice', '<=', to_date),
                                                     ('state', 'in', ['open','paid']),
                                                     ('tipo_comprobante.type', '=', 'credit_note')])
        content = ''
        for invoice in invoice_ids.sorted(key='date_invoice'):
            tax_lines = invoice.tax_line_ids.filtered(lambda x: x.tax_id.is_perception == True and
                                                                x.tax_id.type_aliquot == 'agip')
            if invoice.currency_id != invoice.company_id.currency_id:
                amount_total = invoice._convert_invoice(invoice.currency_id, invoice.amount_total,
                                                        invoice.company_id.currency_id,
                                                        invoice.company_id,
                                                        invoice._get_currency_rate_date() or fields.Date.today())

                amount = invoice._convert_invoice(invoice.currency_id, sum(line.amount for line in tax_lines),
                                                  invoice.company_id.currency_id, invoice.company_id,
                                                  invoice._get_currency_rate_date() or fields.Date.today())
            else:
                amount_total = invoice.amount_total
                amount = sum(line.amount for line in tax_lines)
            if tax_lines:
                base = sum(line.base for line in tax_lines)

                # Tipo de Operacion [1]
                content += "1"
                # Numero de sucursal            [4]
                content += invoice.punto_venta.name.zfill(4)
                # Nro de la nota de credito            [8]
                content += (invoice.num_comprobante or '').zfill(8)
                # Fecha nota de credito      [10] (dd/mm/yyyy)
                content += fields.Date.from_string(invoice.date_invoice).strftime('%d/%m/%Y')
                # Monto de nota de credito            [13]
                content += ('%016.2f' % (amount_total)).replace('.', ',')
                # Nro de certificado propio           [16]
                content += "".ljust(16, " ")
                # Tipo de comprobante      [2]
                content += '01' if not invoice.tipo_comprobante.comprobante_credito else '10'
                # Letra del Comprobante      [1]
                content += invoice.tipo_comprobante.desc if not invoice.tipo_comprobante.comprobante_credito else (invoice.tipo_comprobante.desc in ['A', 'B', 'C'] and invoice.tipo_comprobante.desc or ' ')
                # Numero de sucursal            [5]
                content += invoice.refund_invoice_id.punto_venta.name.zfill(5)
                # Numero Emision Comprobante            [11]
                content += invoice.refund_invoice_id.num_comprobante.zfill(11)
                # Cuit contribuyente Percibido [11]
                content += invoice.partner_id.cuit.replace('-','').zfill(11)
                # Codigo de Norma [3]
                content += (self.company_id.code_perception or '').zfill(3)
                # Fecha Emision Comprobante      [10] (dd/mm/yyyy)
                content += fields.Date.from_string(invoice.refund_invoice_id.date_invoice).strftime('%d/%m/%Y')
                # Monto Retencion/ Percepcion            [16]
                content += ('%016.2f' % (amount)).replace('.', ',')
                # Alícuota           [5]
                content += ('%05.2f' % (tax_lines[0].tax_id.amount)).replace('.', ',')
                content += '\r\n'

        return content

    def _get_document_type(self, partner):
        if partner.documento_id:
            if partner.documento_id.name == 'CUIT':
                return '3'
            elif partner.documento_id.name == 'CUIL':
                return '2'
            elif partner.documento_id.name == 'CDI':
                return '1'
            else:
                return ''
        elif partner.parent_id:
            return partner.parent_id._get_document_type()
        else:
            return ''

    def _get_iibb_type(self, partner):
        if partner.tipo_ingresos_brutos:
            if partner.tipo_ingresos_brutos == 'M':
                return '2'
            elif partner.tipo_ingresos_brutos == 'L':
                return '1'
            else:
                return '4'
        elif partner.parent_id:
            return self._get_iibb_type(partner.parent_id)
        else:
            return '4'

    def _get_responsability_type(self, partner):
        if partner.responsability_id:
            if partner.responsability_id.codigo == '1':
                return '1'
            elif partner.responsability_id.codigo == '4':
                return '3'
            elif partner.responsability_id.codigo == '6':
                return '4'
            else:
                return ''
        elif partner.parent_id:
            return partner.parent_id._get_responsability_type()
        else:
            return ''

    def _get_partner_name(self, partner):
        if partner.parent_id:
            return self._get_partner_name(partner.parent_id)
        elif partner.name:
            return partner.name
        else:
            return ''


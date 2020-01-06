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


class account_aliquot_arba_wizard(models.TransientModel):
    _name = 'account.aliquot.arba.wizard'
    _description = 'Aliquot ARBA Export'

    def _domain_activity_ids(self):
        company = self.env.user.company_id
        if company and company.calculate_pw_arba:
            return [("id", "in", company.activity_ids.ids)]
        return [("id", "=", [])]

    activity_id = fields.Many2one(
        'res.arba.activity',
        string='Activities',
        domain=lambda self: self._domain_activity_ids(),
        required=True
    )

    from_date = fields.Date(
        'From')

    to_date = fields.Date(
        'To')

    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.user.company_id.id,
        required=True)

    type_operation = fields.Selection([
        ('A', 'High'),
        ('B', 'Low'),
        ('M', 'Modification')],
        string='Type operation', required=True, default='A')

    txt_filename = fields.Char()
    txt_binary = fields.Binary()
    is_data = fields.Boolean('Is data')
    mark_declared = fields.Boolean('Declared withholding', help='Mark withholding as declared', default=False)

    @api.onchange('activity_id')
    def onchange_from_date(self):
        currdate = datetime.date.today()
        if self.activity_id and self.activity_id.period == "biweekly":
            if currdate.day <= 15:
                self.from_date = currdate.strftime('%Y-%m-01')
            else:
                self.from_date = (currdate).strftime('%Y-%m-16')
        else:
            self.from_date = currdate.strftime('%Y-%m-01')

    @api.onchange('activity_id')
    def onchange_to_date(self):
        currdate = datetime.date.today()
        if self.activity_id and self.activity_id.period == "biweekly":
            if currdate.day <= 15:
                self.to_date = currdate.strftime('%Y-%m-15')
            else:
                self.to_date = (currdate + relativedelta(day=1, days=-1, months=1)).strftime('%Y-%m-%d')
        else:
            self.to_date = (currdate + relativedelta(day=1, days=-1, months=1)).strftime('%Y-%m-%d')



    @api.multi
    def confirm(self):
        self.ensure_one()

        # build txt filename
        filename_date = self._get_filename_date()
        txt_filename = "AR-" + self.company_id.cuit.replace("-","") + '-' + filename_date + "-" + \
                       self.activity_id.code + '-' + "LOTE1"

        # build txt file
        content = ''
        if self.activity_id.code == '7':
            content = self.get_content_7(self.from_date, self.to_date, self.activity_id.period)
        elif self.activity_id.code == '6':
            content = self.get_content_6(self.from_date, self.to_date, self.mark_declared)

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
            'res_model': 'account.aliquot.arba.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref(
                'l10n_ar_perception_withholding.account_aliquot_arba_wizard_download').id,
            'context': self.env.context,
            'target': 'new',
        }

    def _get_filename_date(self):
        filename_date = self.from_date.strftime('%Y%m')
        # lote = "LOTE1"
        if self.activity_id.period == "monthly":
            filename_date += "0"
        else:
            from_date = self.from_date
            if from_date.day <= 15:
                filename_date += "1"
            else:
                filename_date += "2"
                # lote = "LOTE2"
        return filename_date

    def get_tipo_comprobante(self, invoice):
        if invoice.tipo_comprobante.type == 'invoice':
            if invoice.tipo_comprobante.comprobante_credito:
                return 'E'
            else:
                return 'F'
        elif invoice.tipo_comprobante.type == 'credit_note':
            if invoice.tipo_comprobante.comprobante_credito:
                return 'H'
            else:
                return 'C'
        elif invoice.tipo_comprobante.type == 'debit_note':
            if invoice.tipo_comprobante.comprobante_credito:
                return 'I'
            else:
                return 'D'
        elif invoice.tipo_comprobante.codigo in ['004', '009', '015', '050', '054', '070']:
            return 'R'
        elif invoice.tipo_comprobante.codigo in ['005', '010', '016', '055']:
            return 'V'
        else:
            return ' '

    def get_content_7(self, from_date, to_date, type):
        invoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', from_date),
                                                     ('date_invoice', '<=', to_date),
                                                     ('state', 'in', ['open','paid'])])
        content = ''
        for invoice in invoice_ids.sorted(key='date_invoice'):
            tax_lines = invoice.tax_line_ids.filtered(lambda x: x.tax_id.is_perception == True and
                                                                x.tax_id.type_aliquot == 'arba')
            if tax_lines:
                base = sum(line.base for line in tax_lines)
                # Cuit contribuyente Percibido [13]
                content += invoice.partner_id._get_cuit().zfill(13)
                # Fecha Percepcion      [10] (dd/mm/yyyy)
                content += fields.Date.from_string(
                    invoice.date_invoice).strftime('%d/%m/%Y')
                # Tipo de comprobante            [1]
                content += self.get_tipo_comprobante(invoice)
                # Letra de comprobante            [1]
                content += invoice.tipo_comprobante.desc or ' '
                # Numero de sucursal            [4]
                content += (invoice.punto_venta.name or '').zfill(4)
                # Numero Emision            [8]
                content += (invoice.num_comprobante or '').zfill(8)
                # Monto imponible            [12]
                monto = (base != 0.0 and base or invoice.neto_gravado)
                if invoice.tipo_comprobante.type == 'credit_note':
                    monto *= -1
                content += ('%012.2f' % monto).replace('.', ',')
                # Importe de Percepcion            [11]
                importe = sum(line.amount for line in tax_lines)
                if invoice.tipo_comprobante.type == 'credit_note':
                    importe *= -1
                content += ('%011.2f' % importe).replace('.', ',')
                if type == 'biweekly':
                    # Fecha Emision Comprobante      [10] (dd/mm/yyyy)
                    content += fields.Date.from_string(
                        invoice.date_invoice).strftime('%d/%m/%Y')
                # Tipo Operacion            [1]
                content += self.type_operation
                content += '\r\n'

        return content

    def get_content_6(self, from_date, to_date, mark_declared):
        group_ids = self.env['account.payment.group'].search([('date', '>=', from_date),
                                                     ('date', '<=', to_date),
                                                     ('state', 'in', ['confirmed','posted'])])
        content = ''
        withholding_ids = group_ids.mapped('withholding_arba_id').sorted(key='name')
        for withholding in withholding_ids:
            pay = withholding.payment_id
            group = pay.payment_group_id
            if group.amount_arba_withholding != 0.0:
                # Cuit contribuyente Percibido [13]
                content += group.partner_id._get_cuit().zfill(13)
                # Fecha Emision Comprobante      [10] (dd/mm/yyyy)
                content += fields.Date.from_string(
                    group.date).strftime('%d/%m/%Y')
                # Numero de sucursal            [4]
                content += (self.company_id.branch_number or '').zfill(4)
                # Numero Emision            [8]
                content += withholding.name.zfill(8) if pay else (group.name or '').zfill(8)
                # Importe de Retencion            [11]
                content += ('%011.2f' % group.amount_arba_withholding).replace('.', ',')
                # Tipo Operacion            [ 3]
                content += self.type_operation
                content += '\r\n'
        if mark_declared:
            withholding_ids.action_declared()
        return content

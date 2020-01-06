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
import operator
from odoo import api, fields, models


class account_aliquot_sf_wizard(models.TransientModel):
    _name = 'account.aliquot.sf.wizard'
    _description = 'Aliquot Santa Fe Export'

    def _domain_activity_ids(self):
        company = self.env['res.company'].search([('parent_id', '=', False)], order='id', limit=1)
        if company and company.arba_env_type:
            return [("id", "in", company.activity_ids.ids)]
        return [("id", "=", [])]

    from_date = fields.Date('From', default=datetime.datetime.now().strftime('%Y-%m-01'))

    to_date = fields.Date('To', default=(datetime.datetime.now() + \
                                         relativedelta(months=+1, day=1, days=-1)).strftime('%Y-%m-%d'))
    activity = fields.Selection([
        ('perc', 'Perception'),
        ('with', 'withholding')],
        string='Activities', required=True, default='with')

    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env['res.company'].search([('parent_id', '=', False)], order='id', limit=1),
        required=True)
    calculate_perc_sf = fields.Boolean(related='company_id.calculate_perc_sf', readonly=True)
    calculate_wh_sf = fields.Boolean(related='company_id.calculate_wh_sf', readonly=True)

    txt_filename = fields.Char()
    txt_binary = fields.Binary()
    is_data = fields.Boolean('Is data')

    @api.onchange('company_id')
    def _onchange_invoice_line_ids(self):
        if self.company_id.calculate_perc_sf and self.company_id.calculate_wh_sf:
            self.activity = 'with'
        elif self.company_id.calculate_perc_sf:
            self.activity = 'perc'
        elif self.company_id.calculate_wh_sf:
            self.activity = 'with'

    @api.multi
    def confirm(self):
        self.ensure_one()

        # build txt filename
        txt_filename = "IBRetEmitida_Santa_FE"

        # build txt file
        content = ''
        content = self.get_content(self.from_date, self.to_date, self.activity)

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
            'res_model': 'account.aliquot.sf.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref(
                'l10n_ar_perception_withholding_sf.account_aliquot_sf_wizard_download').id,
            'context': self.env.context,
            'target': 'new',
        }

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
                return '4'
            elif partner.tipo_ingresos_brutos == 'L':
                return '1'
            elif partner.tipo_ingresos_brutos == 'NI':
                return '2'
            else:
                return '3'
        elif partner.parent_id:
            return partner.parent_id._get_iibb_type()
        else:
            return '3'

    def _get_responsability_type(self, partner):
        if partner.responsability_id:
            if partner.responsability_id.codigo == '1':
                return '1'
            elif partner.responsability_id.codigo == '4':
                return '3'
            elif partner.responsability_id.codigo == '6':
                return '4'
            else:
                return '0'
        elif partner.parent_id:
            return partner.parent_id._get_responsability_type()
        else:
            return '0'

    def _get_exemption(self, partner):
        if partner.exempt_sf == 'no_withholding':
            return '1'
        elif partner.exempt_sf == 'exemption':
            return '2'
        elif partner.exempt_sf == 'no_perception':
            return '3'
        elif partner.exempt_sf == 'article':
            return '4'
        else:
            return '0'

    def _get_partner_name(self, partner):
        if partner.parent_id:
            return partner.parent_id._get_partner_name()
        elif partner.name:
            return partner.name
        else:
            return ''

    def get_content(self, from_date, to_date, activity):
        if activity == 'with':
            return self.get_content_group(from_date, to_date)

    def get_content_group(self, from_date, to_date):
        content = ''
        vals = {}
        group_ids = self.env['account.payment.group'].search([('date', '>=', from_date),
                                                              ('date', '<=', to_date),
                                                              ('state', 'in', ['confirmed', 'posted'])], order='date')
        i = 1
        for group in group_ids:
            payment = group.payment_ids.filtered(lambda x: x.type_aliquot == 'sf')
            if group.amount_sf_withholding != 0.0:
                # type_exemption = self._get_exemption(group.partner_id)
                withholding_sf_id = group.withholding_sf_id
                withholding_sf_aliquot = withholding_sf_id.withholding_sf_aliquot
                if withholding_sf_id.withholding_sf_aliquot <= 0.0 and group.partner_id._get_sf_update(group.company_id):
                    withholding_sf_aliquot = group.partner_id._get_sf_update(group.company_id).withholding_aliquot
                vals_payment = {
                    'type_o': "1",
                    'type_c': "1",
                    'number': str(i).zfill(5),
                    'article': withholding_sf_id.article_id.code if withholding_sf_id.article_id else '',
                    'jurisdiction': group.company_id.jurisdiction_id.code if group.company_id.jurisdiction_id else '',
                    'date': group.date,
                    # 'code': group.company_id.article_withholding_id.code or '',
                    # 'code_partner': group.article_id.code or '',
                    # 'voucher_type': '08',
                    # 'voucher_letter': ' ',
                    # 'branch_office': self.company_id.branch_number,
                    # 'certificate': payment.number_sf.zfill(12) if payment else '            ',
                    # 'amount_total': group.amount_total_payable,
                    'voucher_number': self.company_id.branch_number.zfill(4) + group.withholding_sf_id.name.zfill(8),
                    # 'document_type': self._get_document_type(group.partner_id),
                    'cuit': group.partner_id.cuit.replace('-', ''),
                    'iibb_type': self._get_iibb_type(group.partner_id),
                    'iibb_code': group.partner_id.ingresos_brutos or '',
                    # 'responsability_type': self._get_responsability_type(group.partner_id),
                    # 'inscribed_grav': '0',
                    # 'inscribed_drel': '0',
                    'name': self._get_partner_name(group.partner_id),
                    # 'amount_other': group.amount_total_payable - sum(
                    #     line.amount for line in group.payment_ids.filtered(lambda x: x.is_withholding == False)),
                    # 'amount_grav': 0.0,
                    # 'amount_iva': 0.0,
                    # 'amount_drel': 0.0,
                    'amount_untaxed': group.withholding_tax_base_real,
                    'aliquot': withholding_sf_aliquot,
                    'amount': group.amount_sf_withholding,
                    # 'type_exemption': type_exemption,
                    # 'year_exemption': fields.Date.from_string(group.partner_id.date_sf).strftime('%Y') if type_exemption in ('1', '2', '3') else '0000',
                    # 'number_exemption': group.partner_id.certificate_exemption if type_exemption in ('1', '2', '3') else '      ',
                }

                if vals.get(group.date, False):
                    vals[group.date].append(vals_payment)
                else:
                    vals[group.date] = [vals_payment]
                i += 1

        for key, values in sorted(vals.items(), key=operator.itemgetter(0)):
            for value in values:
                # Número de Renglón (único por archivo) [5]
                content += value['number'] + ','
                # Origen del Comprobante     [1]
                content += value['type_o'] + ','
                # Tipo de Comprobante     [1]
                content += value['type_c'] + ','
                # Numero de comprobante            [11]
                content += value['voucher_number'] + ','
                # CUIT Contribuyente involucrado en la transacción Comercial [11]
                content += value['cuit'].zfill(11) + ','
                # Fecha Emision Comprobante      [10] (dd/mm/yyyy)
                content += fields.Date.from_string(value['date']).strftime('%d/%m/%Y') + ','
                # Monto Sujeto a Retención (numérico sin separador de miles)          [9]
                content += ('%.2f' % (value['amount_untaxed'])) + ','
                # Alícuota (porcentaje sin separador de miles)           [3]
                content += ('%.2f' % (value['aliquot'])) + ','
                # Monto Retenido (numérico sin separador de miles, se obtiene de multiplicar el
                # campo 7 por el campo 8 y dividirlo por 100)           [9]
                content += ('%.2f' % (value['amount'])) + ','
                # Tipo de Régimen de Retención (código correspondiente según tabla definida por la
                # jurisdicción) [3]
                content += value['article'].zfill(3) + ','
                # Tipo de Régimen de Retención (código correspondiente según tabla definida por la
                # jurisdicción) [3]
                content += value['jurisdiction'].zfill(3)

                content += '\r\n'

        return content

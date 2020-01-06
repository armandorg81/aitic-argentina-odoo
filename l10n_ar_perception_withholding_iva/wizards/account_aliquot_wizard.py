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


class AccountAliquotiIvaWizard(models.TransientModel):
    _name = 'account.aliquot.iva.wizard'
    _description = 'Aliquot IVA Export'

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
    calculate_perc_iva = fields.Boolean(related='company_id.calculate_perc_iva')
    calculate_wh_iva = fields.Boolean(related='company_id.calculate_wh_iva')

    txt_filename = fields.Char()
    txt_binary = fields.Binary()
    is_data = fields.Boolean('Is data')
    mark_declared = fields.Boolean('Declared withholding', help='Mark withholding as declared', default=False)

    @api.multi
    def confirm(self):
        self.ensure_one()

        # build txt file
        content = self.get_content(self.from_date, self.to_date, self.mark_declared)

        # save file
        bytes_base64_encoded = base64.encodebytes(content.encode('utf-8'))
        is_data = content != '' and True or False
        self.write({
            'txt_filename': '%s.txt' % ('Ret_IVA'),
            'txt_binary': bytes_base64_encoded.decode('utf-8').replace('\n', ''),
            'is_data': is_data
        })
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'res_model': 'account.aliquot.iva.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref(
                'l10n_ar_perception_withholding_iva.account_aliquot_iva_wizard_download').id,
            'context': self.env.context,
            'target': 'new',
        }

    def get_content(self, from_date, to_date, mark_declared):
        withholding_ids = self.env['account.withholding'].search([('date', '>=', from_date),
                                                     ('date', '<=', to_date),
                                                     ('type_aliquot', '=', 'iva')])
        content = ''
        for withholding in withholding_ids:

            if withholding.withholding_amount != 0.0 and withholding.partner_id.regimen_retencion_id:
                # Tipos de comprobante [2]
                content += '06'
                # Fecha Emision Comprobante      [10] (dd/mm/yyyy)
                content += fields.Date.from_string(
                    withholding.date).strftime('%d/%m/%Y')
                # Numero de sucursal            [8]
                content += (self.company_id.branch_number or '').zfill(8)
                # Numero Emision            [8]
                content += withholding.name.zfill(8)
                # Importe de Pago            [13,2]
                # content += ('%016.2f' % withholding.payment_id.amount_total_payable).replace('.', ',')
                content += ('%016.2f' % withholding.payment_group_id.amount_total_payable).replace('.', ',')
                # Codigo de impuesto [3]
                content += '767'
                # Codigo de regimen [3]
                content += withholding.partner_id.regimen_retencion_id.name.zfill(3) if withholding.partner_id.regimen_retencion_id.name else ''.zfill(3)
                # Codigo de operacion [1]
                content += '1'
                # Importe de BaseRetencion            [11,2]
                # content += ('%014.2f' % withholding.payment_id.amount_withholding).replace('.', ',')
                content += ('%014.2f' % withholding.withholding_tax_base_real).replace('.', ',')
                # Fecha Emision Comprobante      [10] (dd/mm/yyyy)
                content += fields.Date.from_string(
                    withholding.date).strftime('%d/%m/%Y')
                # Codigo de condicion [2]
                content += '01'
                # Sujeto suspenso [1]
                content += '0'
                # Importe de Retenido             [11,2]
                content += ('%014.2f' % withholding.withholding_amount).replace('.', ',')
                # Porcentage de exclusion [3,2]
                content += '000,00'
                # Fecha Emision Reporte      [10] (dd/mm/yyyy)
                content += datetime.datetime.now().strftime('%d/%m/%Y')
                # Tipo de documento     [2]
                content += withholding.partner_id.documento_id.codigo.zfill(2) if withholding.partner_id.documento_id.codigo else ''.zfill(2)
                # Cuit contribuyente Percibido [11]
                content += withholding.partner_id._get_cuit().replace('-', '').zfill(11)
                # Espacios en blancos
                content += '         00000000000000                              00000000000000000000000'
                content += '\r\n'

        if mark_declared:
            withholding_ids.action_declared()

        return content
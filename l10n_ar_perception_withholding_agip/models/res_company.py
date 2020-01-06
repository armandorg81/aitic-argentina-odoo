# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
try:
    from pyafipws3.iibb import IIBB
except ImportError:
    IIBB = None
from odoo.exceptions import UserError
import logging
from datetime import datetime
_logger = logging.getLogger(__name__)
import os
from odoo.addons.queue_job.job import job


class ResCompany(models.Model):
    _inherit = "res.company"

    # @api.model
    # def get_supplier_wh_agip_account_id(self):
    #     wh_account = self.env.ref('l10n_ar_perception_withholding_agip.account_account_201050411', False)
    #     return wh_account and wh_account.id or False

    @api.model
    def get_customer_perc_agip_account_id(self):
        wh_account = self.env.ref('l10n_ar_perception_withholding_agip.account_account_201050111', False)
        return wh_account and wh_account.id or False

    @api.model
    def _get_supplier_wh_agip_journal(self):
        companies = self.search([])
        if len(companies) != 1:
            wh_journal = False
        else:
            wh_journal = self.env.ref('l10n_ar_perception_withholding_agip.account_journal_withholding_iibb_agip', False)
            if not wh_journal :
                wh_journal = self.env['account.journal'].search([('code', '=', 'WHCF')])
        return wh_journal and wh_journal.id or False

    # supplier_wh_agip_account_id = fields.Many2one('account.account', 'Withholding account  IIBB CABA', default=get_supplier_wh_agip_account_id,
    #                                          help="Account where the AGIP withholding value will be reflected in the supplier payment")
    calculate_pw_agip = fields.Boolean('AGIP perception withholding agent',
                                       help="The company is AGIP perception withholding agent",
                                       default=True)
    customer_perc_agip_account_id = fields.Many2one('account.account', 'Perception account  IIBB CABA', default=get_customer_perc_agip_account_id,
                                             help="Account where the value of the AGIP perception will be reflected in the customer invoice.")
    directory = fields.Char(string="Directory of the AGIP aliquot file to import")
    supplier_wh_agip_journal_id = fields.Many2one('account.journal', string="Withholding journal IIBB CABA",
                                                  domain=[('type', '=', 'bank')], default=_get_supplier_wh_agip_journal)
    code_withholding = fields.Char(string="Withholding Standard Code")
    code_perception = fields.Char(string="Perception Standard Code")

    @api.multi
    @job
    def _job_generate_line(self, lines):
        # _logger.info("Job #%s" % 1)
        for line in lines:
            partner = self.env['res.partner']
            tax_obj = self.env['account.tax']
            aliquot_obj = self.env['res.aliquot']
            aliquots = self.env['res.aliquot']
            date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            result = line.split(';')
            if len(result) >= 11 and len(result[3]) == 11:
                from_date = result[1][4:] + '-' + result[1][2:4] + '-' + result[1][0:2]
                to_date = result[2][4:] + '-' + result[2][2:4] + '-' + result[2][0:2]
                cuit = result[3]
                self._cr.execute("""INSERT INTO res_aliquot_agip (date_from, date_to, date_update, cuit_taxpayer,
                                        type_ci, mark_hs, mark_aliq, perception_aliquot, withholding_aliquot, perception_group, 
                                        withholding_group) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', %s, %s, %s, %s)""" %
                                 (from_date, to_date, date.strftime('%Y-%m-%d'), result[3],
                                  str(result[4]), str(result[5]), str(result[6]),
                                  result[7].replace(',', '.') != '' and float(result[7].replace(',', '.')) or 0.0,
                                  result[8].replace(',', '.') != '' and float(result[8].replace(',', '.')) or 0.0,
                                  str(result[9]), str(result[10])))
                _logger.info('We get the following data: \n%s' % result[3])
                partner_ids = partner.search([('cuit_origin', '=', cuit)])
                if partner_ids:
                    for partner_id in partner_ids:
                        previous_aliquot = aliquot_obj.search(
                            [('partner_id', '=', partner_id.id), ('company_id', '=', self.id),
                             ('type', '=', 'agip'),
                             ('date_from', '=', from_date),
                             ('date_to', '=', to_date),
                             ('date_update', '<', date.strftime('%Y-%m-%d'))])
                        if not previous_aliquot:
                            data = {
                                'partner_id': partner_id.id,
                                'company_id': self.id,
                                'date_from': from_date,
                                'date_to': to_date,
                                'date_update': date.strftime('%Y-%m-%d'),
                                'cuit_taxpayer': result[3],
                                'type_ci': result[4],
                                'mark_hs': result[5],
                                'mark_aliq': result[6],
                                'perception_aliquot': result[7].replace(',', '.') != '' and float(
                                    result[7].replace(',', '.')) or 0.0,
                                'withholding_aliquot': result[8].replace(',', '.') != '' and float(
                                    result[8].replace(',', '.')) or 0.0,
                                'perception_group': result[9],
                                'withholding_group': result[10],
                                'type': 'agip',
                                'active': True,
                            }
                            _logger.info('We get the following data: \n%s' % data)
                            aliquot = aliquot_obj.create(data)
                            aliquots += aliquot
                            if aliquot.perception_aliquot > 0.0:
                                tax_perception = tax_obj.search(
                                    [('is_perception', '=', True), ('type_aliquot', '=', 'agip'),
                                     ('amount', '=', aliquot.perception_aliquot)])
                                if not tax_perception:
                                    tax_obj.create({
                                        'name': _("Perception AGIP ") + str(aliquot.perception_aliquot) + "%",
                                        'is_perception': True,
                                        'is_iva': False,
                                        'type_tax_use': 'sale',
                                        'description': "PCABA_" + str(aliquot.perception_aliquot).replace('.', ''),
                                        'amount': aliquot.perception_aliquot,
                                        'company_id': self.id,
                                        'account_id': self.customer_perc_agip_account_id.id,
                                        'refund_account_id': self.customer_perc_agip_account_id.id,
                                        'type_aliquot': 'agip',
                                    })
                        else:
                            previous_aliquot.write({
                                'perception_aliquot': result[7].replace(',', '.') != '' and float(
                                    result[7].replace(',', '.')) or 0.0,
                                'withholding_aliquot': result[8].replace(',', '.') != '' and float(
                                    result[8].replace(',', '.')) or 0.0,
                                'perception_group': result[9],
                                'withholding_group': result[10],
                                'date_update': date.strftime('%Y-%m-%d'),
                            })
                            aliquots += previous_aliquot

                    (aliquot_obj.search([('partner_id', 'in', partner_ids.ids), ('company_id', '=', self.id),
                                        ('type', '=', 'agip')]) -  aliquots).write({'active': False})

    @api.one
    def get_agip_data(self):
        partner = self.env['res.partner']
        tax_obj = self.env['account.tax']
        aliquot_obj = self.env['res.aliquot']
        aliquots = self.env['res.aliquot']
        self.ensure_one()
        if self.calculate_pw_agip:
            if not self.directory:
                raise UserError(_('Debe especificar el directorio del archivo de alícuota AGIP a importar.'))
            # archivo = open(os.path.join(self.directory, 'agip.txt'), 'r')
            date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            self._cr.execute('DELETE FROM res_aliquot_agip')
            with open(os.path.join(self.directory, 'agip.txt'), 'r', errors='ignore') as archivo:
                lines = archivo.readlines()
            # for line in archivo.readline():
            #     self.generate_line(line)
                limit = 200
                offset = int(len(lines)/ limit) + 1
                for i in range(0, offset):
                    # _logger.info("Job #%s" % i)
                    start = i * limit
                    stop = start + limit
                    self.with_delay(
                        channel='root.sub_agip',
                        description='Actualizar alícuotas AGIP')._job_generate_line(lines[start:stop])
            archivo.close()
            if aliquots:
                (aliquot_obj.search([('type', '=', 'agip'),('company_id', '=', self.id)]) - aliquots).write({'active': False})
        return True


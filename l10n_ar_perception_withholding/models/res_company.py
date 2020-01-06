# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
try:
    from pyafipws3.iibb import IIBB
except ImportError:
    IIBB = None
from odoo.exceptions import UserError
import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime
_logger = logging.getLogger(__name__)
import os


class ResCompany(models.Model):
    _inherit = "res.company"

    # @api.model
    # def get_supplier_wh_arba_account_id(self):
    #     wh_account = self.env.ref('l10n_ar_perception_withholding.account_account_201050401', False)
    #     return wh_account and wh_account.id or False

    @api.model
    def get_customer_perc_arba_account_id(self):
        wh_account = self.env.ref('l10n_ar_perception_withholding.account_account_201050101', False)
        return wh_account and wh_account.id or False

    @api.model
    def _get_supplier_wh_arba_journal(self):
        companies = self.search([])
        if len(companies) != 1:
            wh_journal = False
        else:
            wh_journal = self.env.ref('l10n_ar_perception_withholding.account_journal_withholding_iibb', False)
            if not wh_journal:
                wh_journal = self.env['account.journal'].search([('code', '=', 'WHBA'),('company_id', '=', self.id)])
        return wh_journal and wh_journal.id or False

    arba_cit_key = fields.Char(string='Arba CIT Key')
    arba_env_type = fields.Many2one('res.arba.config', string='Arba Enviroment Type')
    # supplier_wh_arba_account_id = fields.Many2one('account.account', 'Withholding account IIBB BSAS', default=get_supplier_wh_arba_account_id,
    #                                          help="Account where the ARBA withholding value will be reflected in the supplier payment")
    calculate_pw_arba = fields.Boolean('ARBA perception withholding agent', help="The company is ARBA perception withholding agent.",
                                  default=True)
    customer_perc_arba_account_id = fields.Many2one('account.account', 'Perception account IIBB BSAS', default=get_customer_perc_arba_account_id,
                                             help="Account where the value of the ARBA perception will be reflected in the customer invoice.")
    supplier_wh_arba_journal_id = fields.Many2one('account.journal', string="Withholding journal IIBB BSAS",
                                             domain=[('type', '=', 'bank')], default=_get_supplier_wh_arba_journal)
    directory_arba = fields.Char(string="Directory of the ARBA aliquot file to import")
    is_server = fields.Boolean('Connect to the ARBA web service',
                                       help="If this field is marked to connect to ARBA, it will be done through a web service, but it will be done from the standard that is downloaded from the site.",
                                       default=True)
    arba_crt = fields.Char('Arba Certified')
    # emission_number_arba = fields.Char(string='Init number group payment ARBA')
    activity_ids = fields.Many2many(
        'res.arba.activity',
        string='Activities',
        copy=False,
    )

    @api.one
    def get_arba_data(self):
        self.ensure_one()
        if self.calculate_pw_arba:
            if self.is_server:
                self.get_arba_data_server()
            else:
                self.get_arba_data_off()

    @api.multi
    def arba_connect(self):

        self.ensure_one()
        ws = IIBB()
        if self.cuit:
            cuit = self.cuit.replace('-','')

            if not cuit:
                raise UserError(_(
                    'You must configure CUIT con company %s related partner') % (
                                    self.name))
            if not self.arba_cit_key:
                raise UserError(_(
                    'You must configure ARBA CIT Key on company %s') % (
                                    self.name))

            if not self.arba_env_type:
                raise UserError(_(
                    'You must configure Arba Enviroment Type on company %s') % (
                                    self.name))

            environment_type = self.arba_env_type.enviroment_type

            arba_url = self.arba_env_type.url_connection
            ws.Usuario = cuit
            ws.Password = self.arba_cit_key
            ws.Conectar(url=arba_url, cacert=self.arba_crt or '/opt/odoo/certificados/arba/arba.crt')
            _logger.info(
                'Connection getted to ARBA with url "%s" and CUIT %s' % (
                    arba_url, cuit))
            if ws.CodigoError:
                raise UserError("%s\nError %s: %s" % (
                    ws.MensajeError, ws.TipoError, ws.CodigoError))
        return ws

    @api.one
    def get_arba_data_server(self):
        self.ensure_one()
        if self.calculate_pw_arba:
            partners = self.env['res.partner'].search(["|",('customer', '=', True),('supplier', '=', True)])
            aliquots_obj = self.env['res.aliquot']
            aliquots = self.env['res.aliquot']
            for partner in partners.filtered(lambda x: x.exempt_arba == False and x.documento_id.name == 'CUIT'):
                aliquot = self.get_arba_data_partner(partner)
                if aliquot:
                    aliquots += aliquot
            if aliquots:
                (aliquots_obj.search([('type', '=', 'arba'),('company_id.id', '=', self.id)]) - aliquots).write({'active': False})
        return True

    def get_arba_data_partner(self, partner):
        tax_obj = self.env['account.tax']
        aliquot_obj = self.env['res.aliquot']
        date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
        from_date = date + relativedelta(day=1)
        to_date = date + relativedelta(day=1, days=-1, months=+1)
        if partner.cuit:
            # raise UserError(_('No CUIT cofigured for partner %s') % (
            #     partner.name))
            previous_aliquot = aliquot_obj.search([('partner_id', '=', partner.id), ('company_id', '=', self.id),
                                                   ('type', '=', 'arba'),
                                                   ('date_from', '=', from_date.strftime('%Y-%m-%d')),
                                                   ('date_to', '=', to_date.strftime('%Y-%m-%d')),
                                                   ('date_update', '=', date.strftime('%Y-%m-%d'))])
            if previous_aliquot:
                return previous_aliquot

            cuit = partner.cuit.replace('-', '')

            _logger.info(
                'Getting ARBA data for cuit %s from date %s to date %s' % (
                    from_date, to_date, cuit))
            ws = self.arba_connect()
            ws.ConsultarContribuyentes(
                from_date.strftime('%Y%m%d'),
                to_date.strftime('%Y%m%d'),
                cuit)

            if ws.Excepcion:
                 raise UserError("%s\nExcepcion: %s" % (
                     ws.Traceback, ws.Excepcion))

            if ws.CodigoError:
                return False
                # raise UserError("%s\nError %s: %s" % (
                #     ws.MensajeError, ws.TipoError, ws.CodigoError))

            data = {
                'partner_id': partner.id,
                'company_id': self.id,
                'date_from': from_date.strftime('%Y-%m-%d'),
                'date_to': to_date.strftime('%Y-%m-%d'),
                'date_update': date.strftime('%Y-%m-%d'),
                'voucher_number': ws.NumeroComprobante,
                'hash_code': ws.CodigoHash,
                'cuit_taxpayer': ws.CuitContribuyente,
                'perception_aliquot': ws.AlicuotaPercepcion.replace(',', '.') != '' and float(
                    ws.AlicuotaPercepcion.replace(',', '.')) or 0.0,
                'withholding_aliquot': ws.AlicuotaRetencion.replace(',', '.') != '' and float(
                    ws.AlicuotaRetencion.replace(',', '.')) or 0.0,
                'perception_group': ws.GrupoPercepcion,
                'withholding_group': ws.GrupoRetencion,
                'type': 'arba',
                'active': True,
            }
            _logger.info('We get the following data: \n%s' % data)
            aliquot = aliquot_obj.create(data)
            if aliquot.perception_aliquot > 0.0:
                tax_perception = tax_obj.search([('is_perception', '=', True), ('type_aliquot', '=', 'arba'), ('amount', '=', aliquot.perception_aliquot)])
                if not tax_perception:
                    tax_obj.create({
                        'name': _("Perception ARBA ") + str(aliquot.perception_aliquot) + "%",
                        'is_perception': True,
                        'is_iva': False,
                        'type_tax_use': 'sale',
                        'description': "PBSAS_" + str(aliquot.perception_aliquot).replace('.', ''),
                        'amount': aliquot.perception_aliquot,
                        'company_id': self.id,
                        'account_id': self.customer_perc_arba_account_id.id,
                        'refund_account_id': self.customer_perc_arba_account_id.id,
                        'type_aliquot': 'arba',

                    })

            return aliquot

    @api.one
    def get_arba_data_off(self):
        self.ensure_one()
        if self.calculate_pw_arba:
            if not self.directory_arba:
                raise UserError(_('Debe especificar el directorio del archivo de alícuota ARBA a importar.'))
            archivo = open(os.path.join(self.directory_arba, 'arba_per.txt'), 'r')
            date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            self._cr.execute('DELETE FROM res_aliquot_arba')
            for line in archivo.readlines():
                result = line.split(';')
                if len(result) >= 10 and len(result[4]) == 11:
                    from_date = result[2][4:] + '-' + result[2][2:4] + '-' + result[2][0:2]
                    to_date = result[3][4:] + '-' + result[3][2:4] + '-' + result[3][0:2]
                    cuit = result[4]
                    self._cr.execute("""INSERT INTO res_aliquot_arba (date_from, date_to, date_update, cuit_taxpayer,
                        type_ci, mark_hs, mark_aliq, perception_aliquot, perception_group) VALUES 
                        ('%s', '%s', '%s', '%s', '%s', '%s', '%s', %s, '%s')""" %
                                     (from_date, to_date, date.strftime('%Y-%m-%d'), result[4],
                                      str(result[5]), str(result[6]), str(result[7]),
                                      result[8].replace(',', '.') != '' and float(result[8].replace(',', '.')) or 0.0,
                                      str(result[9])))
                    _logger.info('We get the following data: \n%s' % result[4])
            archivo.close()

            archivo = open(os.path.join(self.directory_arba, 'arba_ret.txt'), 'r')
            for line in archivo.readlines():
                result = line.split(';')
                if len(result) >= 10 and len(result[4]) == 11:
                    from_date = result[2][4:] + '-' + result[2][2:4] + '-' + result[2][0:2]
                    to_date = result[3][4:] + '-' + result[3][2:4] + '-' + result[3][0:2]
                    cuit = result[4]
                    self._cr.execute("""INSERT INTO res_aliquot_arba (date_from, date_to, date_update, cuit_taxpayer,
                        type_ci, mark_hs, mark_aliq, withholding_aliquot, withholding_group) VALUES 
                        ('%s', '%s', '%s', '%s', '%s', '%s', '%s', %s, '%s')""" %
                                     (from_date, to_date, date.strftime('%Y-%m-%d'), result[4],
                                      str(result[5]), str(result[6]), str(result[7]),
                                      result[8].replace(',', '.') != '' and float(result[8].replace(',', '.')) or 0.0,
                                      str(result[9])))
                    _logger.info('We get the following data: \n%s' % result[4])
            archivo.close()

            self.update_arba_partner()

        return True

    def update_arba_partner(self, partner_id=False):
        tax_obj = self.env['account.tax']
        aliquot_obj = self.env['res.aliquot']
        aliquots = self.env['res.aliquot']
        date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
        if partner_id:
            partners = partner_id
        else:
            partners = self.env['res.partner'].search(["|", ('customer', '=', True), ('supplier', '=', True)])
        for partner in partners.filtered(lambda x: x.cuit):
            aliq = self.env['res.aliquot.arba'].search([('cuit_taxpayer', '=', partner.cuit.replace('-', ''))])
            aliq_p = aliq.filtered(lambda x: x.perception_aliquot > 0)
            aliq_w = aliq.filtered(lambda x: x.withholding_aliquot > 0)
            if aliq:
                aliq = aliq[0]
                previous_aliquot = aliquot_obj.search(
                    [('partner_id', '=', partner.id), ('company_id', '=', self.id),
                     ('type', '=', 'arba'),
                     ('date_from', '=', aliq.date_from),
                     ('date_to', '=', aliq.date_to),
                     ('date_update', '<', date.strftime('%Y-%m-%d'))])
                if not previous_aliquot:
                    data = {
                        'partner_id': partner.id,
                        'company_id': self.id,
                        'date_from': aliq.date_from,
                        'date_to': aliq.date_to,
                        'date_update': date.strftime('%Y-%m-%d'),
                        'cuit_taxpayer': aliq.cuit_taxpayer,
                        'type_ci': aliq.type_ci,
                        'mark_hs': aliq.mark_hs,
                        'mark_aliq': aliq.mark_aliq,
                        'perception_aliquot': aliq_p[0].perception_aliquot if aliq_p else 0.0,
                        'withholding_aliquot': aliq_w[0].withholding_aliquot if aliq_w else 0.0,
                        'perception_group': aliq_p[0].perception_group if aliq_p else '',
                        'withholding_group': aliq_w[0].withholding_group if aliq_w else '',
                        'type': 'arba',
                        'active': True,
                    }
                    _logger.info('We get the following data: \n%s' % data)
                    aliquot = aliquot_obj.create(data)
                    aliquots += aliquot
                    if aliquot.perception_aliquot > 0.0:
                        tax_perception = tax_obj.search(
                            [('is_perception', '=', True), ('type_aliquot', '=', 'arba'),
                             ('amount', '=', aliquot.perception_aliquot)])
                        if not tax_perception:
                            tax_obj.create({
                                'name': _("Perception ARBA ") + str(aliquot.perception_aliquot) + "%",
                                'is_perception': True,
                                'is_iva': False,
                                'type_tax_use': 'sale',
                                'description': "PBSAS_" + str(aliquot.perception_aliquot).replace('.', ''),
                                'amount': aliquot.perception_aliquot,
                                'company_id': self.id,
                                'account_id': self.customer_perc_arba_account_id.id,
                                'refund_account_id': self.customer_perc_arba_account_id.id,
                                'type_aliquot': 'arba',
                            })
                else:
                    previous_aliquot.write({
                        'perception_aliquot': aliq.perception_aliquot,
                        'withholding_aliquot': aliq.withholding_aliquot,
                        'perception_group': aliq.perception_group,
                        'withholding_group': aliq.withholding_group,
                        'date_update': date.strftime('%Y-%m-%d'),
                    })

        if aliquots:
            (aliquot_obj.search([('type', '=', 'arba'), ('company_id', '=', self.id)]) - aliquots).write(
                {'active': False})



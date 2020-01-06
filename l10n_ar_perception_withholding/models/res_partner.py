# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz


class ResPartner(models.Model):
    _inherit = "res.partner"

    aliquot_ids = fields.One2many('res.aliquot',
                                    'partner_id',
                                    'Aliquots', domain=lambda self: [('company_id.id', '=', self.env.user.company_id.id)])
    exempt_arba = fields.Boolean(string="Exempt Aliquot Prov. BS. AS.", default=False, company_dependent=True)
    date_arba_from = fields.Date(string='Start date exempt IIBB Prov. BS. AS.', company_dependent=True)
    date_arba_to = fields.Date(string='End date exempt IIBB Prov. BS. AS.', company_dependent=True)

    def get_date_timezone(self, date):
        user_tz = self.env.user.tz if self.env.user.tz else 'America/Argentina/Buenos_Aires'
        tz = pytz.timezone(user_tz)
        field_date = pytz.utc.localize(date).astimezone(tz)
        return field_date

    def get_exempt_arba(self, date=False):
        if not date:
            date = fields.Datetime.now()
            date = self.get_date_timezone(datetime.strptime(date, '%Y-%m-%d %H:%M:%S')).strftime('%Y-%m-%d')
        if self.tipo_ingresos_brutos == 'E':
            return True
        elif self.exempt_arba and self.date_arba_from <= date and self.date_arba_to >= date:
            return True
        else:
            return False

    @api.model
    def _get_arba_update(self, company_id, date=False, report=False):
        if not self.get_exempt_arba(date) or report:
            if report and date:
                arba_aliquot = self.mapped('aliquot_ids').filtered(lambda x: x.type == 'arba' and
                                                                    x.company_id.id == company_id.id and
                                                                    x.date_from <= date and
                                                                    x.date_to >= date).sorted(
                                                                    key=lambda p:(p.date_update), reverse=True)
                if not arba_aliquot:
                    arba_aliquot = self.env['res.aliquot'].search([('type', '=', 'arba'),('active', '=', False),
                                                    ('company_id', '=', company_id.id),('partner_id', '=', self.id),
                                                    ('date_from', '<=', date),('date_to', '>=', date)]).sorted(
                                                                    key=lambda p:(p.date_update), reverse=True)
            else:
                arba_aliquot = self.mapped('aliquot_ids').filtered(lambda x: x.type == 'arba' and
                                                                        x.company_id.id == company_id.id).sorted(key=lambda p:
                                                                        (p.date_update), reverse=True)
            if arba_aliquot:
                return arba_aliquot[0]
            elif self.company_type == 'person' and self.parent_id:
                return self.parent_id._get_arba_update(company_id, date, report)
        return False

    @api.multi
    def update_arba_data_partner(self):
        companies = self.env['res.company'].search([('calculate_pw_arba', '=', True)], order='id')
        if companies:
            date = datetime.now().strftime('%Y-%m-%d')
            partners = self.filtered(lambda x: x.get_exempt_arba(date) == False and x.documento_id.name == 'CUIT')
            for company in companies:
                for rec in partners:
                    if company.is_server:
                        company.get_arba_data_partner(rec)
                    else:
                        company.update_arba_partner(rec)
        return True

    @api.model
    def create(self, vals):
        rec = super(ResPartner, self).create(vals)
        if rec:
            rec.update_arba_data_partner()
        return rec




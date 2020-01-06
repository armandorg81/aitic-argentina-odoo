# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz


class ResPartner(models.Model):
    _inherit = "res.partner"

    exempt_sf = fields.Selection([('none', 'Not exempt'),
                                  ('no_withholding', 'No withholding certificate'),
                                  ('exemption', 'Certificate of exemption'),
                                  ('no_perception', 'Certificate of non-perception'),
                                  ('article', 'Art. 3ero. Res 15/97 y modif.')], string='Type of exemption Santa Fe', default='none')
    date_sf = fields.Date(string='Date exempt IIBB Santa Fe', company_dependent=True)
    certificate_exemption = fields.Char("Certificate of exemption number", size=6)
    aliquot_ids = fields.One2many('res.aliquot',
                                    'partner_id',
                                    'Aliquots', domain=lambda self: [('company_id.id', '=', self.env.user.company_id.id)])

    def get_date_timezone(self, date):
        user_tz = self.env.user.tz if self.env.user.tz else 'America/Argentina/Buenos_Aires'
        tz = pytz.timezone(user_tz)
        field_date = pytz.utc.localize(date).astimezone(tz)
        return field_date

    def get_exempt_sf(self, date=False, type='withholding'):
        if not date:
            date = fields.Datetime.now()
            date = self.get_date_timezone(datetime.strptime(date, '%Y-%m-%d %H:%M:%S')).strftime('%Y-%m-%d')
        if self.tipo_ingresos_brutos == 'E':
            return True
        elif self.exempt_sf == 'article':
            return True
        elif self.exempt_sf == 'no_withholding' and type == 'withholding' and self.date_sf <= date:
            return True
        elif self.exempt_sf == 'no_perception' and type == 'perception' and self.date_sf <= date:
            return True
        elif self.exempt_sf == 'exemption' and self.date_sf <= date:
            return True
        else:
            return False

    @api.model
    def _get_sf_update(self, company_id, date=False, type='withholding', init_data=False):
        if not self.get_exempt_sf(date, type) or init_data:
            sf_aliquot = self.mapped('aliquot_ids').filtered(lambda x: x.type == 'sf' and
                                                                    x.company_id.id == company_id.id).sorted(key=lambda p:
                                                                    (p.date_update), reverse=True)
            if sf_aliquot:
                return sf_aliquot[0]
            elif self.company_type == 'person' and self.parent_id:
                return self.parent_id._get_sf_update(company_id, date, type)
        return False




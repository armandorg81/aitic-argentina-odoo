# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz


class ResPartner(models.Model):
    _inherit = "res.partner"

    exempt_iva = fields.Boolean(string="Exempt Aliquot IVA", default=False, company_dependent=True)
    date_iva_from = fields.Date(string='Start date exempt Perc/Withhol IVA', company_dependent=True)
    date_iva_to = fields.Date(string='End date exempt Perc/Withhol IVA', company_dependent=True)



    def get_exempt_iva(self, date=False):
        if not date:
            date = fields.Datetime.now()
            date = self.get_date_timezone(datetime.strptime(date, '%Y-%m-%d %H:%M:%S')).strftime('%Y-%m-%d')
        if self.tipo_ingresos_brutos == 'E':
            return True
        if self.exempt_iva and (self.date_iva_from <= date and self.date_iva_to >= date):
            return True
        else:
            return False

    @api.model
    def _get_iva_update(self, company_id, date=False):
        if not self.get_exempt_iva(date):
            iva_aliquot = self.mapped('aliquot_ids').filtered(lambda x: x.type == 'iva' and
                                                                         x.company_id.id == company_id.id).sorted(
                                                                        key=lambda p: (p.date_update), reverse=True)
            if iva_aliquot:
                return iva_aliquot[0]
            elif self.company_type == 'person' and self.parent_id:
                return self.parent_id._get_iva_update(company_id, date)
        return False






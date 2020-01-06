# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.osv.expression import get_unaccent_wrapper

class WhResPartner(models.Model):
    _inherit = 'res.partner'

    regimen_retencion_id = fields.Many2one('regimen.retencion', string="Regimen Retención")
    exempt_earning = fields.Boolean(string="Exento de retención de ganancias", default=False, company_dependent=True)
    date_earnings_from = fields.Date(string='Fecha inicio de exclusión de ganancias', company_dependent=True)
    date_earnings_to = fields.Date(string='Fecha fin de exclusión de ganancias', company_dependent=True)
    cuit_origin = fields.Char("Número Documento", size=11, compute='_compute_cuit_origin', store=True)

    @api.one
    @api.depends('cuit')
    def _compute_cuit_origin(self):
        if self.cuit:
            self.cuit_origin = self.cuit.replace("-", "").replace(" ", "").replace(".", "")

    def get_exempt_earnings(self, date=False):
        if not date:
            date = fields.Datetime.now()
            date = self.get_date_timezone(datetime.strptime(date, '%Y-%m-%d %H:%M:%S')).strftime('%Y-%m-%d')
        if not self.inscripto or (self.exempt_earning and self.date_earnings_from <= date and self.date_earnings_to >= date):
            return True
        else:
            return False

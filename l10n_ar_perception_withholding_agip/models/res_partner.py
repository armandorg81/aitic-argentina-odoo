# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime


class ResPartner(models.Model):
    _inherit = "res.partner"

    exempt_agip = fields.Boolean(string="Exempt Aliquot Capital Federal", default=False, company_dependent=True)
    date_agip_from = fields.Date(string='Start date exempt IIBB Capital Federal', company_dependent=True)
    date_agip_to = fields.Date(string='End date exempt IIBB Capital Federal', company_dependent=True)

    def get_exempt_agip(self, date=False):
        if not date:
            date = fields.Datetime.now()
            date = self.get_date_timezone(datetime.strptime(date, '%Y-%m-%d %H:%M:%S')).strftime('%Y-%m-%d')
        if self.tipo_ingresos_brutos == 'E':
            return True
        elif self.exempt_agip and self.date_agip_from <= date and self.date_agip_to >= date:
            return True
        else:
            return False

    @api.model
    def _get_agip_update(self, company_id, date=False):
        if not self.get_exempt_agip(date):
            agip_aliquot = self.mapped('aliquot_ids').filtered(lambda x: x.type == 'agip' and
                                                                    x.company_id.id == company_id.id).sorted(key=lambda p:
                                                                    (p.date_update), reverse=True)
            if agip_aliquot:
                return agip_aliquot[0]
            elif self.company_type == 'person' and self.parent_id:
                return self.parent_id._get_agip_update(company_id, date)
        return False

    @api.model
    def create(self, vals):
        companies = self.env['res.company'].search([('calculate_pw_agip', '=', True)], order='id')
        rec = super(ResPartner, self).create(vals)
        if rec and rec.documento_id.name == "CUIT" and rec.cuit:
            for company in companies:
                aliquot_agip = self.env['res.aliquot.agip'].search([('cuit_taxpayer', '=', rec.cuit_origin)]
                                                                   ).filtered(lambda x: x.perception_aliquot != 0.0
                                                                              and x.withholding_aliquot != 0.0)
                if aliquot_agip:
                    data = {
                        'partner_id': rec.id,
                        'company_id': company.id,
                        'date_from': aliquot_agip[0].date_from,
                        'date_to': aliquot_agip[0].date_to,
                        'date_update': aliquot_agip[0].date_update,
                        'cuit_taxpayer': aliquot_agip[0].cuit_taxpayer,
                        'type_ci': aliquot_agip[0].type_ci,
                        'mark_hs': aliquot_agip[0].mark_hs,
                        'mark_aliq': aliquot_agip[0].mark_aliq,
                        'perception_aliquot': aliquot_agip[0].perception_aliquot,
                        'withholding_aliquot': aliquot_agip[0].withholding_aliquot,
                        'perception_group': aliquot_agip[0].perception_group,
                        'withholding_group': aliquot_agip[0].withholding_group,
                        'type': 'agip',
                        'active': True,
                    }
                    aliquot = self.env['res.aliquot'].create(data)
                    if aliquot.perception_aliquot > 0.0:
                        tax_perception = self.env['account.tax'].search(
                            [('is_perception', '=', True), ('type_aliquot', '=', 'agip'),
                             ('amount', '=', aliquot.perception_aliquot)])
                        if not tax_perception:
                            self.env['account.tax'].create({
                                'name': _("Perception AGIP " + str(aliquot.perception_aliquot) + "%"),
                                'is_perception': True,
                                'is_iva': False,
                                'type_tax_use': 'sale',
                                'description': "PCABA_" + str(aliquot.perception_aliquot).replace('.', ''),
                                'amount': aliquot.perception_aliquot,
                                'company_id': company.id,
                                'account_id': company.customer_perc_agip_account_id.id,
                                'refund_account_id': company.customer_perc_agip_account_id.id,
                                'type_aliquot': 'agip',
                            })
        return rec



# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import ValidationError

class L10nArAccountTax(models.Model):
    _inherit = "account.tax"

    is_iva = fields.Boolean("Impuesto IVA", help="Indica si el impuesto es alicuota IVA",default=True)
    is_excempt = fields.Boolean("Exento", help="Indica si el impuesto es exento")
    tipo_tributo = fields.Selection([
        ('1', 'Impuestos nacionales'),
        ('2', 'Impuestos provinciales'),
        ('3', 'Impuestos municipales'),
        ('4', 'Impuestos Internos'),
        ('99', 'Otro')],
        string='Tipo Tributo',copy=False, help="Tipo Tributo", default='99')
    state_id = fields.Many2one('res.country.state','Provincia',copy=False)
    country_id = fields.Many2one('res.country','Pais',copy=False,
        default=lambda self: self.env.ref('base.ar', raise_if_not_found=False))

    @api.constrains('is_excempt', 'amount')
    def _check_tax_if_excempt(self):
        account_precision = self.env['decimal.precision'].precision_get('Account')
        for tax in self:
            if tax.is_excempt and not float_is_zero(tax.amount, account_precision):
                raise ValidationError('SI EL IMPUESTO ES EXENTO, EL MONTO DEBE SER CERO!')

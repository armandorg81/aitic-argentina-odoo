# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class L10nArReportResCompany(models.Model):
    _inherit = "res.company"

    hide_afip_fields = fields.Boolean('Ocultar campos factura',
        help="Si está habilitado oculta los campos relacionados con la localización argentina en el formato de factura")


    @api.onchange('hide_afip_fields')
    def onchange_hide_afip_fields(self):
        if self.hide_afip_fields is True:
            self.calculate_wh = False
        else:
            self.calculate_wh = True

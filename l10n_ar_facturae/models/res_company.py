# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import datetime


class company_facturae(models.Model):

    _description = "Factura Electronica"
    _inherit = 'res.company'

    ambiente_produccion = fields.Selection(
            [('T','Prueba'),
             ('P','Producción')],
            'Servidor AFIP', size=1, default='T')
    ruta_cert = fields.Char('Ruta Certificado', help="Ruta absoluta del archivo que contiene el certificado (.crt)",
                                default='/opt/odoo/certificados/ghf.crt')
    pass_cert = fields.Char('Llave Privada', help="Ruta absoluta del archivo que contiene la llave privada (.key)",
                                default="/opt/odoo/certificados/ghf.key")
    online_mode = fields.Boolean('Online Mode',
        help='Si esta activo enviará el dte, si no está activo solo contabiliza', default='True')
    off_cae = fields.Boolean('Off-Line CAE')
    use_afip_rate = fields.Boolean('Utilizar Tasa Afip',
        help="Si está habilitado se utilizará la tasa de cambio de la moneda del afip para las operaciones de exportación")
    not_invoice = fields.Boolean(string='No Permitir Facturar')
    cbu = fields.Char(string='No. CBU')

    @api.onchange('off_cae')
    def onchange_off_cae(self):
        if self.off_cae:
            self.online_mode = False



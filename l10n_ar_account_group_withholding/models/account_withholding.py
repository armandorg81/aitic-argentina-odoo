# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _


# class WhAccountInvoice(models.Model):
#     _inherit = "account.invoice"
#
#     withholding_ids = fields.One2many('account.withholding', 'invoice_id', string='Retenciones Asociadas', readonly=True)
    
class AccountWithholding(models.Model):
    _name = "account.withholding"

    name = fields.Char(string='No. de Retencion', required=True, default=_('New'))
    date = fields.Date(string='Fecha', required=True, default=fields.Date.today)
    reference = fields.Char(string='Referencia')
    partner_id = fields.Many2one('res.partner', string='Razon Social')
    cuit = fields.Char(related="partner_id.cuit", string="Número Documento")
    # withholding_line = fields.One2many('account.withholding.line', 'withholding_id', string='Linea de Retenciones')
    payment_id = fields.Many2one('account.payment', string='Pago', required=True, ondelete='cascade')
    payment_group_id = fields.Many2one('account.payment.group', related='payment_id.payment_group_id', string='Payment group', oldname='payment_id')
    invoice_ids = fields.Many2many('account.invoice', string='Facturas Asociadas', readonly=True)
    withholding_tax_base_real = fields.Float(string='Monto Sujeto a Retención',readonly=True)
    withholding_amount = fields.Float(string='Monto Retencion',readonly=True)
    regimen_retencion_id = fields.Many2one('regimen.retencion', string="Regimen Retención")
    state = fields.Selection([('done', 'Done'),('declared', 'Declared'),('annulled', 'Annulled')], string="State", default='done')
    type_aliquot = fields.Selection([('earnings', 'Earnings')], string="Type aliquot", default='earnings')
    company_id = fields.Many2one('res.company', related='payment_group_id.company_id')
    active = fields.Boolean('Active', default=True)

    @api.multi
    def action_declared(self):
        for withholding in self:
            # package.scrap_ids.do_scrap()
            withholding.state = 'declared'
        return True

    @api.multi
    def action_annulled(self):
        for withholding in self:
            # package.scrap_ids.do_scrap()
            withholding.state = 'annulled'
        return True

#
# class AccountWithholdingLine(models.Model):
#     _name = 'account.withholding.line'
#
#     withholding_id = fields.Many2one('account.withholding', string='Retencion', ondelete='cascade', index=True)
#     payment_id = fields.Many2one('account.payment',string='Pago')

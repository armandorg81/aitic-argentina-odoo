# coding: utf-8
import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    type_aliquot = fields.Selection(selection_add=[('sf', 'IIBB Santa Fe')])
    number_sf = fields.Char(string='Number Santa Fe')

    # @api.multi
    # def post(self):
    #     ctx = self.env.context.copy()
    #     ctx['enviar_post'] = True
    #     for rec in self:
    #         if rec.is_withholding and rec.type_aliquot == 'sf':
    #             rec.number_sf = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
    #                 'account.payment.supplier.sf')
    #     res = super(AccountPayment, self).post()
    #     return res

    # def update_number_sf(self):
    #     for rec in self.search([('is_withholding', '=', True), ('type_aliquot', '=', 'sf')]).filtered(lambda y:
    #                                                         y.payment_group_id.state in ['confirmed','posted']).sorted(
    #                                                             key=lambda x:x.payment_group_id.date):
    #         rec.number_sf = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
    #                 'account.payment.supplier.sf')





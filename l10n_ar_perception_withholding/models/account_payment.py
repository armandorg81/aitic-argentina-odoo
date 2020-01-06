# coding: utf-8
import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # amount_aliquot_in_words = fields.Char(string="Amount in Words")
    # is_withholding = fields.Boolean("Withholding", default=False)
    # type_aliquot = fields.Selection([('none', ''), ('arba', 'IIBB Prov. BS. AS.')], default='none')
    type_aliquot = fields.Selection(selection_add=[('arba', 'IIBB Prov. BS. AS.')])
    number_arba = fields.Char(string='Number Arba')

    # @api.multi
    # def post(self):
    #     ctx = self.env.context.copy()
    #     ctx['enviar_post'] = True
    #     for rec in self:
    #         if rec.is_withholding and rec.type_aliquot == 'arba':
    #             rec.number_arba = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
    #                 'account.payment.supplier.arba')
    #     res = super(AccountPayment, self).post()
    #     return res
    #
    # def update_number_arba(self):
    #     for rec in self.search([('is_withholding', '=', True), ('type_aliquot', '=', 'arba')]).filtered(lambda y:
    #                                                         y.payment_group_id.state in ['confirmed','posted']).sorted(
    #                                                             key=lambda x:x.payment_group_id.date):
    #         rec.number_arba = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
    #                 'account.payment.supplier.arba')





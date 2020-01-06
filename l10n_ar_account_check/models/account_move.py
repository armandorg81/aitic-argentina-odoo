# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    check_id = fields.Many2one(
        'account.check',
        string='Check',
        copy=False
    )

    check_operation = fields.Char(string="Check Operation", copy=False)

    @api.multi
    def post(self, invoice=False):
        res = super(AccountMove, self).post(invoice=invoice)
        for rec in self:
            if rec.check_id and self.check_operation == 'use':
                rec.check_id._create_operation(self.check_operation, rec, date=rec.date)
        return res

    @api.model
    def create(self, vals):
        rec = super(AccountMove, self).create(vals)
        if rec.check_id:
            rec.check_id.write({'move_id': rec.id})
        return rec


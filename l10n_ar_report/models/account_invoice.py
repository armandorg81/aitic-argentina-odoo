# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models, _
from .common import to_word

class L10nArReportAccountInvoice(models.Model):
    _inherit = "account.invoice"

    stock_picking_ids = fields.Many2many('stock.picking', compute='_compute_invoice_picking', string='Receptions', compute_sudo=True)

    @api.multi
    @api.depends('amount_total')
    def _get_word_amount(self):
        for inv in self:
            inv.word_amount = to_word(math.floor(inv.amount_total),None)

    @api.multi
    def _compute_invoice_picking(self):
        for invoice in self:
            pickings = False
            if invoice.origin:
                pickings = invoice.env['sale.order'].search([('name', 'like', invoice.origin), ('company_id', '=', invoice.company_id.id), ('state', 'in', ['sale', 'done'])]).mapped('picking_ids').filtered(lambda s: s.state == 'done')
            invoice.stock_picking_ids = pickings

    @api.multi
    def invoice_print(self):
        self.ensure_one()
        self.sent = True
        return self.env.ref('l10n_ar_report.l10n_ar_account_invoices').report_action(self)

    word_amount = fields.Char('Importe de', compute="_get_word_amount",store=True)

    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('l10n_ar_report.l10n_ar_email_template_edi_invoice', False)
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            force_email=True
        )
        return {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

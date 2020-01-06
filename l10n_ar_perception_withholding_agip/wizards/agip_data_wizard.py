# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from datetime import datetime
import os
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class wizard_agip_data(models.TransientModel):
   
    _name = 'wizard.agip.data'
    _description = 'Wizard to update the aliquots of IIBB of Federer Capital.'

    def _default_company_id(self):
        companies = self.env['res.company'].search([('parent_id', '=', False)], order='id', limit=1)
        if companies:
            return companies.id
        return self.env['res.company']

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self._default_company_id())
    
        
    def import_file(self):
        if self and self.company_id:
            return self.company_id.get_agip_data()



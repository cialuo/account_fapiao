# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################
from openerp import models, fields, api, _

class account_voucher(models.Model):
    _inherit = 'account.voucher'


    fapiao_id = fields.Many2many('account.fapiao',string=u'发票号码')



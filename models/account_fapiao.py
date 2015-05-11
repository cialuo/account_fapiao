# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_fapiao(models.Model):
    _name = "account.fapiao"
    _inherit = ['mail.thread']
    _order = "fapiao_date desc,id desc"


    name=fields.Integer(string="Fapiao Number", required=True)
    fapiao_date=fields.Date(string="Fapiao Date", required=True,default=fields.Date.today)
    category_id=fields.Many2one('res.partner.category',string=u'发票抬头',required=True)
    amount_with_taxes = fields.Float('Fapiao total amount', compute='_compute_amount_with_taxes')
    notes=fields.Text(string="Notes")
    partner_id=fields.Many2one('res.partner',string='Partner')
    fapiao_line_id=fields.One2many('account.fapiao.line','fapiao_id')
    isrefund = fields.Boolean(string=u'开退票')
    original_name = fields.Many2one('account.fapiao',string=u'原始号码')
    paid = fields.Boolean(string=u'已回款')
    paid_date= fields.Date(string=u'回款时间')
    state= fields.Selection([
        ('draft','Draft'),
        ('confirmed','Confirmed'),
        ('refunded','Refunded'),
        ('cancel','Cancel')
    ], string=u'状态',default='draft')


    @api.multi
    def unlink(self):
        for fapiao in self:
            if fapiao.state not in ('draft'):
                raise Warning(_('非草稿状态不能删除'))
        return super(account_fapiao, self).unlink()

    # @api.multi
    # def create(self):
    #     for fapiao in self:
    #         if fapiao.fapiao_line_id.amount == 0:
    #             del fapiao.fapiao_line_id



    @api.one
    @api.depends('fapiao_line_id')
    def _compute_amount_with_taxes(self):
        if self.fapiao_line_id:
            self.amount_with_taxes = sum((l.amount for l in self.fapiao_line_id))

    def _compute_balance(self,line,amount_original):

        if line:
            subtotal_fapiao_line_amount=0
            #过滤掉取消,草稿的金额 
            fapiao_line= self.env['account.fapiao.line'].search([('move_line_id','=',line.id),('fapiao_id.state','in',['confirmed','refunded'])])
            print '554,',fapiao_line
            if fapiao_line:
                for item in fapiao_line:
                    print '23',item.amount
                    subtotal_fapiao_line_amount = subtotal_fapiao_line_amount + item.amount
                amount_unreconciled = amount_original-subtotal_fapiao_line_amount
            else:
                amount_unreconciled = amount_original
            return amount_unreconciled


    @api.one
    @api.onchange('partner_id')
    def onchange_partner_id(self):

        if self.partner_id and not self.isrefund:
            res=[]
            move_lines= self.env['account.move.line'].search([('state','=','valid'),('partner_id','=',self.partner_id.id),('account_id.type','not in',['receivable'])])
            # move_lines= self.env['account.move.line'].search([('state','=','valid'),('partner_id','=',self.partner_id.id),('account_id.code','=','6')])

            print '445',move_lines
            for line in move_lines:
                if  int(line.account_id.code[0:2])== 60 :
                    print '443',line
                    #r如果在贷方, 就是为正, 如果代借方, 为负, 区别销售和销退
                    if line.credit != 0 and line.debit == 0:
                        amount_original=line.credit
                        # pass
                    if line.credit ==0 and line.debit !=0:
                        amount_original=-line.debit

                    if line.credit ==0 and line.debit ==0:
                        amount_original=0.00

                    #计算未开发票余额
                    print '455',amount_original
                    amount_unreconciled=self._compute_balance(line,amount_original)
                    invoice_obj=self.env['account.invoice'].search([('move_id','=',line.move_id.id)])
                    contact_partner_id = invoice_obj.partner_id
                    invoice_id = invoice_obj.id
                    #不显示余额为0的明细
                    print 'amount_unreconciled',amount_unreconciled
                    if int(amount_unreconciled) !=0 :
                        res.append({ 'move_line_id': line.id,'contact_partner_id':contact_partner_id,'invoice_id':invoice_id,'quantity':line.quantity, 'amount_original':amount_original,'amount_unreconciled':amount_unreconciled,'product_id':line.product_id })
            print '888',res
            self.fapiao_line_id = res
        print self.fapiao_line_id


    @api.one
    @api.onchange('original_name')
    def onchange_original_name(self):
        print '544',self.original_name.name
        fapiao = self.env['account.fapiao'].search([('name','=',self.original_name.name)])
        self.partner_id = fapiao.partner_id
        self.category_id = fapiao.category_id
        res=[]
        for l in fapiao.fapiao_line_id:
            print '5543',l.move_line_id
            res.append({'move_line_id':l.move_line_id,'amount_original':l.amount_original,'quantity':-l.quantity,'amount':-l.amount})

        self.fapiao_line_id =res



    @api.one
    def fapiao_confirmed(self):
        return self.write({'state': 'confirmed'})

    @api.one
    def fapiao_cancel(self):
        return self.write({'state':'cancel'})

    @api.one
    def fapiao_refunded(self):
        return self.write({'state':'refunded'})



class account_fapiao_line(models.Model):
    _name = "account.fapiao.line"


    fapiao_id = fields.Many2one('account.fapiao')
    move_line_id=fields.Many2one('account.move.line',string=u'单号')
    contact_partner_id =fields.Many2one('res.partner')
    move_id= fields.Many2one('account.move',related='move_line_id.move_id', store=True,readonly='True')
    invoice_id=fields.Many2one('account.invoice')
    product_id= fields.Many2one('product.product',string=u'产品')
    quantity=fields.Float()
    amount_original=fields.Float()
    amount_unreconciled= fields.Float()
    reconcile = fields.Boolean()
    amount=fields.Float(string=u'本次开票')

    @api.onchange('reconcile')
    def onchange_reconcile(self):
        self.amount = 0.00
        if self.reconcile:
            self.amount = self.amount_original

    # @api.onchange('move_line_id')
    # def onchange_quantity_move_line_id(self):
    #     print '4455',self.move_line_id,self.move_line_id.quantity
    #     if self.move_line_id:
    #         self.quantity = self.move_line_id.quantity

    @api.one
    @api.onchange('amount')
    def onchange_amount(self):
        amount_with_taxes = 0.00
        print '55'
        amount_with_taxes=self.amount+ amount_with_taxes
        print '77',self.amount,amount_with_taxes
        self.fapiao_id=[{'amount_with_taxes':10}]
        print '88',self.fapiao_id







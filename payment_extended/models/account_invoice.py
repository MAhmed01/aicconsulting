# -*- coding: utf-8 -*-

from odoo import models,fields,api

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.depends('invoice_line_ids')
    def _total_payment(self):
        for record in self:
            if record.invoice_line_ids:
                record.tot_cash = sum(record.mapped('invoice_line_ids.cash'))
                record.tot_credit_card = sum(record.mapped('invoice_line_ids.credit_card'))
                record.tot_voucher = sum(record.mapped('invoice_line_ids.voucher'))
                record.tot_mobile = sum(record.mapped('invoice_line_ids.mobile'))
                record.tot_eft = sum(record.mapped('invoice_line_ids.eft'))

    tot_cash = fields.Float(compute='_total_payment', string='Total Cash', readonly=True, store=True)
    tot_credit_card = fields.Float(compute='_total_payment', string='Total Credit', readonly=True, store=True)
    tot_voucher = fields.Float(compute='_total_payment', string='Total Voucher', readonly=True, store=True)
    tot_mobile = fields.Float(compute='_total_payment', string='Total Mobile', readonly=True, store=True)
    tot_eft = fields.Float(compute='_total_payment', string='Total Eft', readonly=True, store=True)


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"
    
    cash = fields.Float("Cash")
    credit_card = fields.Float("Bank")
    voucher = fields.Float("Voucher")
    mobile = fields.Float("Mobile")
    eft = fields.Float("EFT")
    

class AccountPayment(models.Model):
    _inherit = "account.payment"


    @api.onchange('journal_id')
    def onchange_code(self):
        for rec in self:
            if rec.journal_id.name == 'Bank':
                rec.amount = rec.mapped('invoice_ids').tot_credit_card
            if rec.journal_id.name == 'Cash':
                rec.amount = rec.mapped('invoice_ids').tot_cash
            if rec.journal_id.name == 'Voucher':
                print("rec.journal_id.name",rec.journal_id.name)
                rec.amount = rec.mapped('invoice_ids').tot_voucher
            if rec.journal_id.name == 'Mobile':
                print("rec.journal_id.name",rec.journal_id.name)
                rec.amount = rec.mapped('invoice_ids').tot_mobile
            if rec.journal_id.name == 'EFT':
                print("rec.journal_id.name",rec.journal_id.name)
                rec.amount = rec.mapped('invoice_ids').tot_eft


# -*- coding: utf-8 -*-
from odoo import api, fields, models  # type: ignore
from random import randint
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class IsSuiviTresorerie(models.Model):
    _name='is.suivi.tresorerie'
    _description = "Suivi trésorerie"
    _rec_name = 'mois'
    _order='mois desc'

    mois          = fields.Char('Mois', required=True, index=True)

    montant_achat = fields.Float('Montant achats dus')
    montant_vente = fields.Float('Montant factures client en attente')
    solde         = fields.Float('Solde')
    montant_achat_ce_jour = fields.Float('Montant achats dus à ce jour')
    montant_vente_ce_jour = fields.Float('Montant factures client en attente à ce jour')
    solde_ce_jour         = fields.Float('Solde à ce jour')
    active        = fields.Boolean('Actif', default=True)
    commentaire   = fields.Text('Commentaire')
    

    def actualiser_suivi_tresorerie_action(self):
        today = date.today()
        #** Factures de ventes ************************************************
        domain=[
            ('move_type'      ,'in', ['out_invoice','out_refund']),
            ('state'          ,'=' , 'posted'),
            ('payment_state'  ,'!=', 'paid'),
            ('is_date_abandon','=' , False),
        ]
        invoices = self.env['account.move'].search(domain)
        res={}
        for invoice in invoices:
            mois = str(invoice.invoice_date_due or '')[0:7]
            if mois not in res:
                res[mois]={'montant_achat':0, 'montant_vente':0, 'montant_achat_ce_jour':0, 'montant_vente_ce_jour':0}
            res[mois]['montant_vente']+=invoice.amount_residual_signed
            if invoice.invoice_date_due<today:
                res[mois]['montant_vente_ce_jour']+=invoice.amount_residual_signed

        #** Factures d'achats *************************************************
        domain=[
            ('move_type'    ,'in' , ['in_invoice','in_refund']),
            ('state'        ,'=' , 'posted'),
        ]
        invoices = self.env['account.move'].search(domain)
        for invoice in invoices:
            test=True
            if invoice.is_traite_id:
                ladate = invoice.is_traite_id.date_reglement or invoice.is_traite_id.date_retour
                if ladate<today:
                    test=False
            else:
                ladate = invoice.invoice_date_due
                if invoice.payment_state=='paid':
                    test=False
            if test:
                mois = str(ladate or '')[0:7]
                if mois not in res:
                    res[mois]={'montant_achat':0, 'montant_vente':0, 'montant_achat_ce_jour':0, 'montant_vente_ce_jour':0}
                res[mois]['montant_achat']+=invoice.amount_residual_signed

                if ladate<today:
                    res[mois]['montant_achat_ce_jour']+=invoice.amount_residual_signed

        #** Mise à jour des données *******************************************
        for mois in res:
            montant_achat = -res[mois]['montant_achat']
            montant_vente = res[mois]['montant_vente']
            solde = montant_vente-montant_achat
            montant_achat_ce_jour = -res[mois]['montant_achat_ce_jour']
            montant_vente_ce_jour = res[mois]['montant_vente_ce_jour']
            solde_ce_jour = montant_vente_ce_jour-montant_achat_ce_jour
            vals={
                'mois'         : mois,
                'montant_achat': montant_achat,
                'montant_vente': montant_vente,
                'solde'        : solde,
                'montant_achat_ce_jour': montant_achat_ce_jour,
                'montant_vente_ce_jour': montant_vente_ce_jour,
                'solde_ce_jour'        : solde_ce_jour,
                'active'               : True
            }
            domain=[
                ('mois'  ,'=' , mois),
                ('active','in', [True,False])
            ]
            suivis = self.env['is.suivi.tresorerie'].search(domain)
            if len(suivis)>0:
                for suivi in suivis:
                    suivi.write(vals)
            else:
                self.env['is.suivi.tresorerie'].create(vals)

        #** Archivage des anciens mois ****************************************
        lesmois=[]
        for mois in res:
            lesmois.append(mois)
        suivis = self.env['is.suivi.tresorerie'].search([])
        for suivi in  suivis:
            if suivi.solde==0 and suivi.montant_achat==0 and suivi.montant_vente==0:
                suivi.active=False
            if suivi.mois not in lesmois:
                suivi.active=False





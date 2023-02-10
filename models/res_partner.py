# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import datetime

class IsStatut(models.Model):
    _name='is.statut'
    _description = "Statut"
    _order='name'

    name = fields.Char('Statut', required=True, index=True)


class IsProfil(models.Model):
    _name='is.profil'
    _description = "Profil"
    _order='name'

    name = fields.Char('Profil', required=True, index=True)


class IsOrigine(models.Model):
    _name='is.origine'
    _description = "Origine DP"
    _order='name'

    name = fields.Char('Origine DP', required=True, index=True)


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_statut_id           = fields.Many2one('is.statut' , 'Statut')
    is_profil_id           = fields.Many2one('is.profil' , 'Profil')
    is_origine_id          = fields.Many2one('is.origine', 'Origine DP')
    is_condition_tarifaire = fields.Text('Conditions tarifaire', help="Informations sur les conditions tarifaires affichées sur la commande")
    is_banque_id           = fields.Many2one('account.journal', 'Banque par défaut', domain=[('type','=','bank')])
    is_compte_auxiliaire   = fields.Char('Compte auxiliaire', help="Code du fournisseur ou client pour l'export en compta")

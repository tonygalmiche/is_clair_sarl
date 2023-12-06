# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import datetime
import re

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
    is_modele_commande_id  = fields.Many2one('is.modele.commande' , 'Modèle de commande')
    is_adresse             = fields.Text("Adresse complète", store=True, readonly=True, compute='_compute_is_adresse')
    is_affaire_ids         = fields.One2many('is.affaire', 'client_id', 'Affaires')



    @api.depends('name', 'street','street2','city','zip')
    def _compute_is_adresse(self):
        for obj in self:
            adresse = '%s\n%s\n%s'%((obj.name or ''), (obj.street or ''), (obj.street2 or ''))
            if obj.zip or obj.city:
                adresse += '\n%s - %s'%((obj.zip or ''), (obj.city or ''))
            adresse = re.sub('\\n+','\n',adresse) # Supprimer les \n en double
            obj.is_adresse = adresse


    def creer_modele_commande(self):
        for obj in self:
            vals={
                'name'  : obj.name,
            }
            modele=self.env['is.modele.commande'].create(vals)
            obj.is_modele_commande_id = modele.id
            modele.initialiser_action()

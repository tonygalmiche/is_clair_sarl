# -*- coding: utf-8 -*-
from odoo import fields, models


class IsFamille(models.Model):
    _name='is.famille'
    _description = "Famille"
    _order='name'

    name = fields.Char('Famille', required=True, index=True)


class IsSousFamille(models.Model):
    _name='is.sous.famille'
    _description = "Sous-famille"
    _order='name'

    name = fields.Char('Sous-famille', required=True, index=True)


class product_template(models.Model):
    _inherit = "product.template"
    _order="name"

    is_tache                = fields.Boolean("Tache")
    is_famille_id           = fields.Many2one('is.famille', 'Famille')
    is_sous_famille_id      = fields.Many2one('is.sous.famille', 'Sous-famille')
    is_longueur             = fields.Integer("Longueur")
    is_largeur_utile        = fields.Integer("Largeur utile (mm)")
    is_surface_panneau      = fields.Integer("Surface Panneau")
    is_surface_palette      = fields.Integer("Surface Palette")
    is_poids                = fields.Float("Poids"        , digits=(14,2))
    is_poids_rouleau        = fields.Float("Poids Rouleau", digits=(14,2))
    is_ondes                = fields.Integer("Ondes")
    is_resistance_thermique = fields.Float("Résistance thermique (R)", digits=(14,2))


#     • Fournisseur	
#     • Surface Panneau	
#     • Surface Palette	
#     • Longueur	
#     • Poids Rouleau		
# Famille : Liste de choix =>Colonne B	
# Sous-Famille : Liste de choix => Lignes bleu	
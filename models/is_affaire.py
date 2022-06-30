# -*- coding: utf-8 -*-
from odoo import fields, models
from random import randint


class IsNatureTravaux(models.Model):
    _name='is.nature.travaux'
    _description = "Nature des travaux"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name  = fields.Char('Nature des travaux', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IsTypeTravaux(models.Model):
    _name='is.type.travaux'
    _description = "Type des travaux"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name  = fields.Char('Type des travaux', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IsSpecificite(models.Model):
    _name='is.specificite'
    _description = "Spécificité"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Spécificité', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IsAffaire(models.Model):
    _name='is.affaire'
    _description = "Affaire"
    _order='name desc'

    name               = fields.Char("N° d'Affaire", required=True, index=True, help="Sous la forme AA-XXXX")
    nom                = fields.Char("Nom de l'affaire")
    date_creation      = fields.Date("Date de création", default=lambda *a: fields.Date.today())
    lieu               = fields.Char("Lieu")
    client_id          = fields.Many2one('res.partner' , 'Client')
    chantier_id        = fields.Many2one('res.partner' , 'Adresse du chantier')
    nature_travaux_ids = fields.Many2many('is.nature.travaux', 'is_affaire_nature_travaux_rel', 'affaire_id', 'nature_id'     , string="Nature des travaux")
    type_travaux_ids   = fields.Many2many('is.type.travaux'  , 'is_affaire_type_travaux_rel'  , 'affaire_id', 'type_id'       , string="Type des travaux")
    specificite_ids    = fields.Many2many('is.specificite'   , 'is_affaire_specificite_rel'   , 'affaire_id', 'specificite_id', string="Spécificités")
    commentaire        = fields.Text("Commentaire")


#     • Nature des travaux : Liste de choix « Famille de travaux => Choix multiples
#     • Type de travaux : Liste de choix => Choix multiples



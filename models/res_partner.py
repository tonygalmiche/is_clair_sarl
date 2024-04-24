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

    is_statut_id                = fields.Many2one('is.statut' , 'Statut')
    is_profil_id                = fields.Many2one('is.profil' , 'Profil')
    is_origine_id               = fields.Many2one('is.origine', 'Origine DP')
    is_condition_tarifaire      = fields.Text('Conditions tarifaire', help="Informations sur les conditions tarifaires affichées sur la commande")
    is_banque_id                = fields.Many2one('account.journal', 'Banque par défaut', domain=[('type','=','bank')])
    is_compte_auxiliaire        = fields.Char('Compte auxiliaire fournisseur', help="Code du fournisseur pour l'export en compta")
    is_compte_auxiliaire_client = fields.Char('Compte auxiliaire client'     , help="Code du client pour l'export en compta")
    is_modele_commande_id       = fields.Many2one('is.modele.commande' , 'Modèle de commande')
    is_adresse                  = fields.Text("Adresse complète", store=True, readonly=True, compute='_compute_is_adresse')
    is_affaire_ids              = fields.One2many('is.affaire', 'client_id', 'Affaires')
    is_sale_order_ids           = fields.One2many('sale.order', 'partner_id', 'Commandes client')
    is_type_paiement            = fields.Selection([
        ('traite'      , 'Traite'),
        ('virement'    , 'Virement'),
        ('cheque'      , 'Chèque'),
        ('prelevement' , 'Prélèvement automatique'),
    ], 'Type de paiement')


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



    # @api.model
    # def _address_fields(self):
    #     """Returns the list of address fields that are synced from the parent."""
    #     res = list(super(ResPartner, self)._address_fields())
    #     print("TEST 1 : res=",res)
    #     if 'country_id' in res:
    #         res.remove('country_id')
    #     print("TEST 2 : res=",res)
    #     return res

    # def _prepare_display_address(self, without_company=False):
    #     # res = super(ResPartner, self)._prepare_display_address(without_company=without_company)
    #     # print(res)
    #     # return res

    # def _prepare_display_address(self, without_company=False):
    #     # get the information that will be injected into the display format
    #     # get the address format
    #     address_format = self._get_address_format()
    #     args = {
    #         'state_code': self.state_id.code or '',
    #         'state_name': self.state_id.name or '',
    #         #'country_code': self.country_id.code or '',
    #         #'country_name': self._get_country_name(),
    #         'country_code': False,
    #         'country_name':False,
    #         'company_name': self.commercial_company_name or '',
    #     }
    #     for field in self._formatting_address_fields():
    #         args[field] = getattr(self, field) or ''
    #     if without_company:
    #         args['company_name'] = ''
    #     elif self.commercial_company_name:
    #         address_format = '%(company_name)s\n' + address_format
    #     return address_format, args

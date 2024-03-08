# -*- coding: utf-8 -*-
from odoo import api, fields, models
from random import randint
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange


class IsNatureTravaux(models.Model):
    _name='is.equipe'
    _description = "Equipe"
    _order='name'

    # def _get_default_color(self):
    #     return randint(1, 11)

    name  = fields.Char('Equipe', required=True, index=True)
    color = fields.Char('Couleur')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Cette équipe exite déjà !"),
    ]


class IsChantier(models.Model):
    _name='is.chantier'
    _description = "Chantiers"
    _order='name'

    name              = fields.Char('N°', index=True, readonly=True)
    affaire_id        = fields.Many2one('is.affaire', 'Affaire', required=False)
    equipe_id         = fields.Many2one('is.equipe', 'Equipe', required=False)
    equipe_color      = fields.Char('Couleur', help='Couleur Equipe', related="equipe_id.color")
    nature_travaux_id = fields.Many2one('is.nature.travaux', string="Nature des travaux", required=False)
    date_debut        = fields.Date('Date début', required=False)
    duree             = fields.Integer('Durée')
    date_fin          = fields.Date('Date fin', required=False)
    commentaire       = fields.Char('Commentaire')


    @api.onchange('date_debut')
    def onchange_date_debut(self):
        for obj in self:
            if obj.date_debut and obj.duree:
                obj.date_fin = obj.date_debut + timedelta(days=obj.duree)

    @api.onchange('duree')
    def onchange_duree(self):
        for obj in self:
            if obj.date_debut and obj.duree:
                obj.date_fin = obj.date_debut + timedelta(days=obj.duree)

    @api.onchange('date_fin')
    def onchange_date_fin(self):
        for obj in self:
            if obj.date_fin and obj.duree:
                obj.date_debut = obj.date_fin - timedelta(days=obj.duree)

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('is.chantier')
        res = super(IsChantier, self).create(vals)
        return res



    @api.model
    def move_chantier(self,chantierid=False,debut=False,decale_planning=0):
        if chantierid and debut:
            chantiers = self.env['is.chantier'].search([('id', '=',chantierid)])
            for chantier in chantiers:
                now = date.today()
                jour = now.isoweekday()
                debut_planning = now - timedelta(days=(jour-1)) + timedelta(days=decale_planning)
                date_debut = debut_planning + timedelta(days=debut)
                chantier.date_debut = date_debut
        return 'OK'


    def ajouter_alerte_action(self):
        date=self.date_debut - timedelta(days=1)
        res= {
            'name': 'Alerte',
            'view_mode': 'form',
            'res_model': 'is.chantier.alerte',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'default_chantier_id':self.id, 'default_date':date},
        }
        return res



    @api.model
    def get_chantiers(self,domain,decale_planning=0, nb_semaines=16):#, res_model, ):

        #** Recherche des alertes *********************************************
        lines=self.env['is.chantier.alerte'].search([])
        alertes={}
        for line in lines:
            chantier_id = line.chantier_id.id
            date_alerte = line.date

            if chantier_id not in alertes:
                alertes[chantier_id]={}
            if date_alerte not in alertes[chantier_id]:
                alertes[chantier_id][date_alerte]=[]
            alertes[chantier_id][date_alerte].append(line.alerte)
        #**********************************************************************

        try:
            nb_semaines = int(nb_semaines)
        except:
            nb_semaines = 16
        if nb_semaines<4:
            nb_semaines=4
        if nb_semaines>40:
            nb_semaines=40
        nb_jours = nb_semaines*7
        now = date.today()
        jour = now.isoweekday()
        debut = now - timedelta(days=(jour-1)) + timedelta(days=decale_planning)
        debut_planning = debut
        fin_planning = debut + timedelta(days=nb_jours)

        #** Calcul du nombre de jours dans le mois pour le  colspan ***********
        mois={}
        jour = debut
        for x in range(0,nb_jours):
            if jour==debut or jour.day==1:
                nb_jours_dans_mois = monthrange(jour.year,jour.month)[1]
                if jour==debut:
                    colspan = nb_jours_dans_mois - jour.day +1
                if jour.day==1:
                    colspan = nb_jours_dans_mois
                vals={
                    "key"    : str(jour),
                    "mois"   : jour.strftime('%m/%Y'),
                    "colspan": colspan,
                }
                mois[str(jour)]=vals
            jour = jour + timedelta(days=1)
        #**********************************************************************

        #** Calcul du nombre de jours dans les semaines pour le  colspan ******
        semaines={}
        jour = debut
        for x in range(0,nb_jours):
            if jour.isoweekday()==1:
                nb_jours_dans_semaine = 7
            if jour==debut:
                nb_jours_dans_semaine = 7 - jour.isoweekday() + 1
            if jour==debut or jour.isoweekday()==1:
                colspan = nb_jours_dans_semaine
                vals={
                    "key"    : str(jour),
                    "semaine": jour.strftime('S%W'),
                    "jour"   : jour.strftime('%d'),
                    "colspan": colspan,
                }
                semaines[str(jour)]=vals
            jour = jour + timedelta(days=1)
        #**********************************************************************

        res=[]
        chantiers=self.env['is.chantier'].search(domain, order="name") #, limit=10)
        trcolor=""
        dict={}
        for chantier in chantiers:
            #** Recherhce si le chantier est visible sur le planning **********
            test=False
            if chantier.date_debut>=debut_planning and chantier.date_debut<=fin_planning:
                test=True
            if chantier.date_fin>=debut_planning and chantier.date_fin<=fin_planning:
                test=True
            if chantier.date_debut<=debut_planning and chantier.date_fin>=fin_planning:
                test=True
            #******************************************************************
            if test:
                decal = (chantier.date_debut - debut_planning).days
                if decal<0:
                    decal=0
                if trcolor=="#ffffff":
                    trcolor="#f2f3f4"
                else:
                    trcolor="#ffffff"
                trstyle="background-color:%s"%(trcolor)
                color = chantier.equipe_id.color or 'GreenYellow'
                jours={}

                duree = chantier.duree or (chantier.date_fin - chantier.date_debut).days
                if duree<1:
                    duree=1
                debut = decal+1
                fin = decal + duree 
                for i in range(0, nb_jours):
                    date_jour = debut_planning+timedelta(days=i)
                    alerte=False
                    if chantier.id in alertes:
                        if date_jour in alertes[chantier.id]:
                            alerte = alertes[chantier.id][date_jour]
                    if alerte:
                        alerte='\n'.join(alerte)
                    border="none"
                    if i%7==0:
                        border="1px solid gray"
                    jour={
                        "key"      : i,
                        "color"    : "none",
                        "cursor"   : "default",
                        "border"   : border,
                        "date_jour": date_jour.strftime('%d/%m'),
                        "alerte"   : alerte,
                    }
                    if i>=decal and i<(decal+duree-1):
                        jour["color"]  = color
                        jour["cursor"] = "move"
                        jour["border"] = "none"
                    if i==(decal+duree-1):
                        jour["color"]  = color
                        jour["cursor"] = "col-resize"
                        jour["border"] = "none"
                    jours[i]=jour
                name=chantier.commentaire or chantier.name
                if chantier.affaire_id:
                    name=chantier.affaire_id.name_get()[0][1]
                #name       = chantier.affaire_id.nom or chantier.commentaire or chantier.name
                short_name = name[0:40]

                vals={
                    "id"        : chantier.id,
                    "debut"     : debut,
                    "fin"       : fin,
                    "duree"     : duree,
                    "name"      : name,
                    "short_name": short_name,
                    "equipe"    : (chantier.equipe_id.name or '')[0:15],
                    "travaux"   : (chantier.nature_travaux_id.name or '')[0:15],
                    "trstyle"   : trstyle,
                    "jours"     : jours,
                }
                res.append(vals)
                dict[chantier.id]=vals
        return {
            "dict"       : dict,
            "mois"       : mois,
            "semaines"   : semaines,
            "nb_semaines": nb_semaines,
        }
    


class IsChantierAlerte(models.Model):
    _name='is.chantier.alerte'
    _description = "Alertes pour les chantiers"
    _order='id desc'


    chantier_id = fields.Many2one('is.chantier', 'Chantier', required=True, index=True)
    affaire_id  = fields.Many2one(related="chantier_id.affaire_id")
    alerte      = fields.Text('Alerte'                     , required=True)
    date        = fields.Date('Date alerte', default=fields.Datetime.now, index=True, help="Date à laquelle l'alerte sera positionnée sur le planning des chantiers")


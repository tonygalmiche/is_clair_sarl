# -*- coding: utf-8 -*-
from odoo import api, fields, models
from random import randint
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange
import base64


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


    # def write(self, vals):
    #     res = super(IsChantier, self).write(vals)
    #     return res


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


    @api.model
    def modif_duree_chantier(self,chantierid=False,duree=False):
        if chantierid and duree:
            chantiers = self.env['is.chantier'].search([('id', '=',chantierid)])
            for chantier in chantiers:
                chantier.duree = duree
                chantier.onchange_duree()
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
    def get_chantiers(self,domain=[],decale_planning="", nb_semaines=""):#, res_model, ):
        if nb_semaines=="":
            nb_semaines = self.env['is.mem.var'].get(self._uid, 'chantier_nb_semaine') or 16
        else:
            self.env['is.mem.var'].set(self._uid, 'chantier_nb_semaine', nb_semaines)
        if decale_planning=="":
            decale_planning = self.env['is.mem.var'].get(self._uid, 'chantier_decale_planning') or 16
        else:
            self.env['is.mem.var'].set(self._uid, 'chantier_decale_planning', decale_planning)


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

        try:
            decale_planning = int(decale_planning)
        except:
            decale_planning = 0

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


        #** Recherche de la date de début de chaque affaire pour le tri *******
        date_debut_affaire={}
        chantiers=self.env['is.chantier'].search(domain)
        for chantier in chantiers:
            affaire_id = chantier.affaire_id.id or 0
            if affaire_id not in date_debut_affaire:
                date_debut_affaire[affaire_id]=chantier.date_debut
            if date_debut_affaire[affaire_id]>chantier.date_debut:
                date_debut_affaire[affaire_id]=chantier.date_debut
        #**********************************************************************


        #** Dictionnaire trié des chantiers par date début affaire ***********
        chantiers=self.env['is.chantier'].search(domain)
        my_dict={}
        for chantier in chantiers:
            affaire_id = chantier.affaire_id.id or 0
            date_affaire = date_debut_affaire[affaire_id]
            key = "%s-%s-%s-%s"%(date_affaire,chantier.affaire_id.name,chantier.date_debut,chantier.name)
            my_dict[key]=chantier
        sorted_chantiers = dict(sorted(my_dict.items()))
        #**********************************************************************


        #** Contruction du dictionnaire finale des données dans le bon ordre **
        trcolor="#ffffff"
        mem_affaire=False
        res=[]
        my_dict={}
        width_jour = str(round(66/nb_jours,1))+"%"
        for k in sorted_chantiers:
            chantier = sorted_chantiers[k]
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
                #** Changement de couleur à chaque affaire ********************
                if not mem_affaire:
                    mem_affaire=chantier.affaire_id
                if mem_affaire!=chantier.affaire_id:
                    mem_affaire=chantier.affaire_id
                    if trcolor=="#ffffff":
                        trcolor="#f2f3f4"
                    else:
                        trcolor="#ffffff"
                trstyle="background-color:%s"%(trcolor)
                color = chantier.equipe_id.color or 'GreenYellow'
                #**************************************************************

                decal = (chantier.date_debut - debut_planning).days
                if decal<0:
                    decal=0
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
                        "width"    : width_jour,
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
                short_name = name[0:40]
                affaire_id = chantier.affaire_id.id or 0
                date_affaire = date_debut_affaire[affaire_id]
                key = "%s-%s-%s-%s"%(date_affaire,chantier.affaire_id.name,chantier.date_debut,chantier.name)
                vals={
                    "key"       : key,
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
                my_dict[key]=vals
        sorted_dict = dict(sorted(my_dict.items()))
        return {
            "dict"           : sorted_dict,
            "mois"           : mois,
            "semaines"       : semaines,
            "nb_semaines"    : nb_semaines,
            "decale_planning": decale_planning,
        }
    

    @api.model
    def get_planning_pdf(self):
        #** Recherche du premier chantier pour générer le planning PDF
        chantiers = self.env['is.chantier'].search([],limit=1)

        if len(chantiers)>0:
            chantier_id = chantiers[0].id
            pdf = self.env.ref('is_clair_sarl.is_chantier_reports')._render_qweb_pdf(chantier_id)[0]
            datas = base64.b64encode(pdf).decode()

            # ** Recherche si une pièce jointe est déja associèe *******************
            attachment_obj = self.env['ir.attachment']
            name="planning_chantiers_%s.pdf"%self._uid
            attachments = attachment_obj.search([('name','=',name)],limit=1)
            # **********************************************************************

            # ** Creation ou modification de la pièce jointe ***********************
            vals = {
                'name':  name,
                'type':  'binary',
                'datas': datas,
            }
            if attachments:
                for attachment in attachments:
                    attachment.write(vals)
                    attachment_id=attachment.id
            else:
                attachment = attachment_obj.create(vals)
                attachment_id=attachment.id
            #***********************************************************************
            return attachment_id


    def creation_auto_chantier_cron(self):
        today = date.today()
        filtre=[
            ('state','=','commande'),
            ('type_affaire','=','chantier')
        ]
        lines = self.env['is.affaire'].search(filtre)
        affaires=[]
        for line in lines:
            affaires.append(line)
        chantiers = self.env['is.chantier'].search([])
        affaires_chantiers=[]
        for chantier in chantiers:
            if chantier.affaire_id not in affaires_chantiers:
                affaires_chantiers.append(chantier.affaire_id)
        ct=1
        for affaire in affaires:
            if affaire not in affaires_chantiers:
                vals={
                    "affaire_id": affaire.id,
                    "date_debut": today,
                    "duree": 21,
                }
                chantier = self.env['is.chantier'].create(vals)
                chantier.onchange_duree()
                ct+=1

        #** Recaler à la date du jour les chantiers non plannifiés ***********
        filtre=[
            ('equipe_id' ,'=',False),
            ('date_debut','!=',today),
        ]
        chantiers = self.env['is.chantier'].search(filtre)
        for chantier in chantiers:
            vals={
                "date_debut": today,
                #"duree"     : 21,
            }
            chantier.write(vals)
            chantier.onchange_date_debut()
        #**********************************************************************


class IsChantierAlerte(models.Model):
    _name='is.chantier.alerte'
    _description = "Alertes pour les chantiers"
    _order='id desc'


    chantier_id = fields.Many2one('is.chantier', 'Chantier', required=True, index=True)
    affaire_id  = fields.Many2one(related="chantier_id.affaire_id")
    alerte      = fields.Text('Alerte'                     , required=True)
    date        = fields.Date('Date alerte', default=fields.Datetime.now, index=True, help="Date à laquelle l'alerte sera positionnée sur le planning des chantiers")


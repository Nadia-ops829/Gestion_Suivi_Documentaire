from django.db import models
from django.conf import settings

class BEX(models.Model):
    class TypeBex(models.TextChoices):
        LOCAL = 'LOCAL', 'Local'
        MARITIME = 'MARITIME', 'Maritime'
        AERIEN = 'AERIEN', 'Aérien'
        HORS_BEX = 'HORS_BEX', 'Hors BEX'

    class StatutBex(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        POINTE = 'POINTE', 'Pointé'
        VALIDE = 'VALIDE', 'Validé'
        RECEPTIONNE = 'RECEPTIONNE', 'Réceptionné'
        DEDOUANE = 'DEDOUANE', 'Dédouané'
        PRET_RECEPTION = 'PRET_RECEPTION', 'Prêt pour réception'
        BLOQUE = 'BLOQUE', 'Bloqué'

    numero_bex = models.CharField(max_length=50, unique=True)
    type_bex = models.CharField(max_length=20, choices=TypeBex.choices, default=TypeBex.MARITIME)
    fournisseur = models.CharField(max_length=255)
    date_creation = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=25, choices=StatutBex.choices, default=StatutBex.EN_ATTENTE)
    
    date_enlevement_prevue = models.DateField(null=True, blank=True)
    statut_douanier = models.CharField(max_length=50, default='En attente')
    observations = models.TextField(null=True, blank=True)

    agent_createur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='bex_crees')
    date_pointage_pharmacien = models.DateTimeField(null=True, blank=True)
    pharmacien = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bex_pointes')
    date_reception_rsi = models.DateTimeField(null=True, blank=True)
    rsi = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bex_receptionnes')

    def __str__(self):
        return f"{self.numero_bex} ({self.fournisseur})"

    class Meta:
        verbose_name = "BEX"
        verbose_name_plural = "BEX"

class BEXItem(models.Model):
    bex = models.ForeignKey(BEX, on_delete=models.CASCADE, related_name='items')
    numero_conteneur = models.CharField(max_length=50)
    designation_produit = models.TextField()
    quantite = models.PositiveIntegerField()
    facture_fcfa = models.DecimalField(max_digits=20, decimal_places=2)

    def __str__(self):
        return f"{self.bex.numero_bex} - {self.designation_produit}"

class Conteneur(models.Model):
    numero_conteneur = models.CharField(max_length=50)
    bex = models.ForeignKey(BEX, on_delete=models.CASCADE, related_name='conteneurs')
    def __str__(self): return self.numero_conteneur

class ADI(models.Model):
    class StatutADI(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        SOUMIS = 'SOUMIS', 'Soumis'
        VALIDE = 'VALIDE', 'Validé'
        REJETE = 'REJETE', 'Rejeté'

    numero_adi = models.CharField(max_length=50, unique=True)
    bex = models.ForeignKey(BEX, on_delete=models.CASCADE, related_name='adis', null=True, blank=True)
    fournisseur = models.CharField(max_length=255, null=True, blank=True)
    pays = models.CharField(max_length=100, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    organisme_emetteur = models.CharField(max_length=100, default='ANRP')
    observations = models.TextField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=StatutADI.choices, default=StatutADI.EN_ATTENTE)
    agent_createur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='adis_crees')

    def __str__(self): return self.numero_adi

class CCPQ(models.Model):
    class StatutCCPQ(models.TextChoices):
        NON_DEMARRE = 'NON_DEMARRE', 'Non démarré'
        EN_ANALYSE = 'EN_ANALYSE', 'En analyse'
        APPROUVE = 'APPROUVE', 'Approuvé'
        REJETE = 'REJETE', 'Rejeté'

    numero_ccpq = models.CharField(max_length=50, unique=True)
    bex = models.ForeignKey(BEX, on_delete=models.CASCADE, related_name='ccpqs', null=True, blank=True)
    date_depot = models.DateField(null=True, blank=True)
    date_resultat = models.DateField(null=True, blank=True)
    resultat = models.TextField(null=True, blank=True)
    motif_rejet = models.TextField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=StatutCCPQ.choices, default=StatutCCPQ.NON_DEMARRE)
    agent_createur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ccpqs_crees')

    def __str__(self): return self.numero_ccpq

class DocumentTransit(models.Model):
    class TypeDoc(models.TextChoices):
        FACTURE = 'FACTURE', 'Facture'
        ADI = 'ADI', 'ADI'
        CCPQ = 'CCPQ', 'CCPQ'
        REC165 = 'REC165', 'REC165'
        LIQUIDATION = 'LIQUIDATION', 'Liquidation douanière'
        AUTRE = 'AUTRE', 'Autre'

    class FormatDoc(models.TextChoices):
        PHYSIQUE = 'PHYSIQUE', 'Physique'
        NUMERIQUE = 'NUMERIQUE', 'Numérique'

    bex = models.ForeignKey(BEX, on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    conteneur = models.ForeignKey(Conteneur, on_delete=models.CASCADE, related_name='documents_conteneur', null=True, blank=True)
    fichier = models.FileField(upload_to='transit/documents/')
    type_document = models.CharField(max_length=50, choices=TypeDoc.choices)
    format = models.CharField(max_length=20, choices=FormatDoc.choices, default=FormatDoc.NUMERIQUE)
    date_upload = models.DateTimeField(auto_now_add=True)
    agent_createur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        parent = self.bex.numero_bex if self.bex else (self.conteneur.numero_conteneur if self.conteneur else "N/A")
        return f"{self.type_document} - {parent}"

# Signaux pour les automatismes
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=DocumentTransit)
def update_bex_status_on_upload(sender, instance, created, **kwargs):
    if created and instance.bex:
        bex = instance.bex
        if instance.type_document == DocumentTransit.TypeDoc.LIQUIDATION:
            bex.statut = BEX.StatutBex.DEDOUANE
            bex.save()
        elif instance.type_document == DocumentTransit.TypeDoc.REC165:
            bex.statut = BEX.StatutBex.PRET_RECEPTION
            bex.save()

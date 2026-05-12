from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DocumentTransit, BEX

@receiver(post_save, sender=DocumentTransit)
def update_bex_status_on_document_upload(sender, instance, created, **kwargs):
    """
    Change automatiquement le statut du BEX dès qu'un document de type 
    Liquidation douanière ou REC165 est ajouté.
    """
    if created and instance.bex:
        bex = instance.bex
        if instance.type_document == DocumentTransit.TypeDoc.LIQUIDATION:
            bex.statut = BEX.StatutBex.DEDOUANE
            bex.save()
        elif instance.type_document == DocumentTransit.TypeDoc.REC165:
            bex.statut = BEX.StatutBex.PRET_RECEPTION
            bex.save()

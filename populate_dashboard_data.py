import os
import django
import datetime
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_Suivi_Documentaire.settings')
django.setup()

from users.models import User
from transit.models import BEX, BEXItem, Conteneur, ADI, CCPQ, DocumentTransit

def populate_data():
    print("Début du peuplement de la base de données...")
    
    # 1. Ensure test users exist
    agent1, _ = User.objects.get_or_create(
        username='agent1',
        defaults={
            'first_name': 'Jean',
            'last_name': 'Transit',
            'role': User.Role.AGENT,
            'is_staff': True
        }
    )
    if _:
        agent1.set_password('agent123')
        agent1.save()
        print("Utilisateur agent1 créé.")
        
    chef1, _ = User.objects.get_or_create(
        username='chef1',
        defaults={
            'first_name': 'Marie',
            'last_name': 'Validation',
            'role': User.Role.CHEF_SERVICE,
            'is_staff': True
        }
    )
    if _:
        chef1.set_password('chef123')
        chef1.save()
        print("Utilisateur chef1 créé.")
        
    admin, _ = User.objects.get_or_create(
        username='admin',
        defaults={
            'first_name': 'Admin',
            'last_name': 'RSI',
            'role': User.Role.ADMIN,
            'is_staff': True,
            'is_superuser': True
        }
    )
    if _:
        admin.set_password('admin123')
        admin.save()
        print("Utilisateur admin créé.")

    # Clean existing data to avoid duplicates and have clean trends
    print("Nettoyage des anciennes données transit...")
    DocumentTransit.objects.all().delete()
    BEXItem.objects.all().delete()
    Conteneur.objects.all().delete()
    ADI.objects.all().delete()
    CCPQ.objects.all().delete()
    BEX.objects.all().delete()

    now = timezone.now()

    # Helpers to compute precise datetimes
    def days_ago(d):
        return now - timedelta(days=d)

    # 2. CREATE BEX DOSSIERS
    
    # BEX 1: Maritime, Completed in time (10 days duration), DEDOUANE
    bex1 = BEX.objects.create(
        numero_bex="BEX-2026-001",
        type_bex=BEX.TypeBex.MARITIME,
        fournisseur="SANOFI France",
        statut=BEX.StatutBex.DEDOUANE,
        statut_douanier="Dédouané",
        date_enlevement_prevue=days_ago(15).date(),
        observations="Dossier traité rapidement par l'agent.",
        agent_createur=agent1,
        date_pointage_pharmacien=days_ago(20),
        pharmacien=chef1,
        date_reception_rsi=days_ago(15),
        rsi=admin
    )
    bex1.date_creation = days_ago(25)
    bex1.save()
    
    # BEX 2: Aérien, Completed late (18 days duration), DEDOUANE (Threshold is 15 days)
    bex2 = BEX.objects.create(
        numero_bex="BEX-2026-002",
        type_bex=BEX.TypeBex.AERIEN,
        fournisseur="GLAXOSMITHKLINE",
        statut=BEX.StatutBex.DEDOUANE,
        statut_douanier="Dédouané",
        date_enlevement_prevue=days_ago(10).date(),
        observations="Retard douanier important suite à un problème de manifeste.",
        agent_createur=agent1,
        date_pointage_pharmacien=days_ago(18),
        pharmacien=chef1,
        date_reception_rsi=days_ago(10),
        rsi=admin
    )
    bex2.date_creation = days_ago(28)
    bex2.save()
    
    # BEX 3: Local, Active, In Time (3 days old), EN_ATTENTE
    bex3 = BEX.objects.create(
        numero_bex="BEX-2026-003",
        type_bex=BEX.TypeBex.LOCAL,
        fournisseur="PFIZER Africa",
        statut=BEX.StatutBex.EN_ATTENTE,
        statut_douanier="En attente",
        date_enlevement_prevue=days_ago(-3).date(),
        observations="Attente des documents originaux.",
        agent_createur=agent1
    )
    bex3.date_creation = days_ago(3)
    bex3.save()
    
    # BEX 4: Maritime, Active, Late (20 days old, Threshold is 15 days), BLOQUE
    bex4 = BEX.objects.create(
        numero_bex="BEX-2026-004",
        type_bex=BEX.TypeBex.MARITIME,
        fournisseur="NOVARTIS Pharma",
        statut=BEX.StatutBex.BLOQUE,
        statut_douanier="Bloqué en douane",
        date_enlevement_prevue=days_ago(5).date(),
        observations="Bloqué en douane pour non-conformité de la facture.",
        agent_createur=agent1
    )
    bex4.date_creation = days_ago(20)
    bex4.save()
    
    # BEX 5: Maritime, Active, Late (18 days old, Threshold is 15 days), VALIDE (Late but not in BLOQUE status)
    bex5 = BEX.objects.create(
        numero_bex="BEX-2026-005",
        type_bex=BEX.TypeBex.MARITIME,
        fournisseur="ASTRAZENECA Ltd",
        statut=BEX.StatutBex.VALIDE,
        statut_douanier="En attente liquidation",
        date_enlevement_prevue=days_ago(2).date(),
        observations="Validation effectuée par le pharmacien, en attente de la douane.",
        agent_createur=agent1,
        date_pointage_pharmacien=days_ago(12),
        pharmacien=chef1
    )
    bex5.date_creation = days_ago(18)
    bex5.save()
    
    # BEX 6: Hors BEX, Completed this week (5 days duration), PRET_RECEPTION
    bex6 = BEX.objects.create(
        numero_bex="BEX-2026-006",
        type_bex=BEX.TypeBex.HORS_BEX,
        fournisseur="MERCK Group",
        statut=BEX.StatutBex.PRET_RECEPTION,
        statut_douanier="Visé",
        date_enlevement_prevue=days_ago(1).date(),
        observations="Prêt à être enlevé.",
        agent_createur=agent1,
        date_pointage_pharmacien=days_ago(3),
        pharmacien=chef1,
        date_reception_rsi=days_ago(1),
        rsi=admin
    )
    bex6.date_creation = days_ago(6)
    bex6.save()

    # BEX 7: Maritime, Completed this week (12 days duration), DEDOUANE
    bex7 = BEX.objects.create(
        numero_bex="BEX-2026-007",
        type_bex=BEX.TypeBex.MARITIME,
        fournisseur="ROCHE Diagnostics",
        statut=BEX.StatutBex.DEDOUANE,
        statut_douanier="Dédouané",
        date_enlevement_prevue=days_ago(2).date(),
        observations="Dossier standard dédouané sans encombre.",
        agent_createur=agent1,
        date_pointage_pharmacien=days_ago(8),
        pharmacien=chef1,
        date_reception_rsi=days_ago(2),
        rsi=admin
    )
    bex7.date_creation = days_ago(14)
    bex7.save()

    # 3. CREATE BEX ITEMS & CONTENEURS
    items_data = [
        (bex1, "CONT-001", "Amoxicilline 500mg Gélules", 5000, 3250000.00),
        (bex1, "CONT-001", "Paracétamol 500mg Comprimés", 10000, 1500000.00),
        (bex2, "CONT-002", "Vaxigrip Tetra Vaccins", 2000, 12800000.00),
        (bex3, "CONT-003", "Augmentin Enfant Sirop", 1500, 4800000.00),
        (bex4, "CONT-004", "Voltaren Emulgel 1%", 8000, 6400000.00),
        (bex5, "CONT-005", "Spasfon Injectable", 4000, 2100000.00),
        (bex6, "CONT-006", "Doliprane 1000mg", 12000, 2400000.00),
        (bex7, "CONT-007", "Gaviscon Suspension Buvable", 6000, 3900000.00),
    ]

    for bex, cont_num, product, qty, cost in items_data:
        BEXItem.objects.create(
            bex=bex,
            numero_conteneur=cont_num,
            designation_produit=product,
            quantite=qty,
            facture_fcfa=cost
        )
        Conteneur.objects.get_or_create(
            bex=bex,
            numero_conteneur=cont_num
        )
    print("Conteneurs et items créés.")

    # 4. CREATE DOCUMENTS FOR COMPLETED BEX (to register exact completion dates)
    # BEX 1 completed 15 days ago
    doc1 = DocumentTransit.objects.create(
        bex=bex1,
        fichier="transit/documents/liquidation_bex1.pdf",
        type_document=DocumentTransit.TypeDoc.LIQUIDATION,
        format=DocumentTransit.FormatDoc.NUMERIQUE,
        agent_createur=agent1
    )
    doc1.date_upload = days_ago(15)
    doc1.save()

    # BEX 2 completed 10 days ago
    doc2 = DocumentTransit.objects.create(
        bex=bex2,
        fichier="transit/documents/liquidation_bex2.pdf",
        type_document=DocumentTransit.TypeDoc.LIQUIDATION,
        format=DocumentTransit.FormatDoc.NUMERIQUE,
        agent_createur=agent1
    )
    doc2.date_upload = days_ago(10)
    doc2.save()

    # BEX 6 completed 1 day ago (REC165)
    doc6 = DocumentTransit.objects.create(
        bex=bex6,
        fichier="transit/documents/rec165_bex6.pdf",
        type_document=DocumentTransit.TypeDoc.REC165,
        format=DocumentTransit.FormatDoc.NUMERIQUE,
        agent_createur=agent1
    )
    doc6.date_upload = days_ago(1)
    doc6.save()

    # BEX 7 completed 2 days ago (Liquidation)
    doc7 = DocumentTransit.objects.create(
        bex=bex7,
        fichier="transit/documents/liquidation_bex7.pdf",
        type_document=DocumentTransit.TypeDoc.LIQUIDATION,
        format=DocumentTransit.FormatDoc.NUMERIQUE,
        agent_createur=agent1
    )
    doc7.date_upload = days_ago(2)
    doc7.save()

    print("Documents d'intégration créés.")

    # 5. CREATE ADI DOSSIERS (Threshold = 5 days)
    
    # ADI 1 (linked to bex1): Completed in time (3 days duration)
    ADI.objects.create(
        numero_adi="ADI-2026-001",
        bex=bex1,
        fournisseur="SANOFI France",
        factures="FAC-SANOFI-001",
        nb_items=2,
        quantite=15000,
        cout=4750000.00,
        pays="France",
        date_depot=days_ago(24).date(),
        date_reception=days_ago(21).date(),
        statut=ADI.StatutADI.VALIDE,
        agent_createur=agent1
    )

    # ADI 2 (linked to bex2): Completed late (8 days duration)
    ADI.objects.create(
        numero_adi="ADI-2026-002",
        bex=bex2,
        fournisseur="GLAXOSMITHKLINE",
        factures="FAC-GSK-002",
        nb_items=1,
        quantite=2000,
        cout=12800000.00,
        pays="Royaume-Uni",
        date_depot=days_ago(27).date(),
        date_reception=days_ago(19).date(),
        statut=ADI.StatutADI.VALIDE,
        agent_createur=agent1
    )

    # ADI 3 (linked to bex4): Active, Late (18 days old, Threshold is 5 days)
    ADI.objects.create(
        numero_adi="ADI-2026-003",
        bex=bex4,
        fournisseur="NOVARTIS Pharma",
        factures="FAC-NOV-003",
        nb_items=1,
        quantite=8000,
        cout=6400000.00,
        pays="Suisse",
        date_depot=days_ago(18).date(),
        statut=ADI.StatutADI.EN_ATTENTE,
        agent_createur=agent1
    )

    # ADI 4 (linked to bex5): Active, In Time (2 days old)
    ADI.objects.create(
        numero_adi="ADI-2026-004",
        bex=bex5,
        fournisseur="ASTRAZENECA Ltd",
        factures="FAC-AZ-004",
        nb_items=1,
        quantite=4000,
        cout=2100000.00,
        pays="Suède",
        date_depot=days_ago(2).date(),
        statut=ADI.StatutADI.SOUMIS,
        agent_createur=agent1
    )

    # ADI 5 (Independent): Completed this week (4 days duration)
    ADI.objects.create(
        numero_adi="ADI-2026-005",
        fournisseur="GENERIC LABS",
        factures="FAC-GEN-005",
        nb_items=5,
        quantite=25000,
        cout=8500000.00,
        pays="Inde",
        date_depot=days_ago(8).date(),
        date_reception=days_ago(4).date(),
        statut=ADI.StatutADI.VALIDE,
        agent_createur=agent1
    )

    print("Dossiers ADI créés.")

    # 6. CREATE CCPQ DOSSIERS (Threshold = 7 days)
    
    # CCPQ 1 (linked to bex1): Completed in time (4 days duration)
    CCPQ.objects.create(
        numero_ccpq="CCPQ-2026-001",
        bex=bex1,
        date_depot=days_ago(23).date(),
        date_resultat=days_ago(19).date(),
        resultat="Certificat de Contrôle de Qualité Conforme.",
        statut=CCPQ.StatutCCPQ.APPROUVE,
        agent_createur=agent1
    )

    # CCPQ 2 (linked to bex2): Completed late (10 days duration)
    CCPQ.objects.create(
        numero_ccpq="CCPQ-2026-002",
        bex=bex2,
        date_depot=days_ago(26).date(),
        date_resultat=days_ago(16).date(),
        resultat="Approuvé après contre-analyse.",
        statut=CCPQ.StatutCCPQ.APPROUVE,
        agent_createur=agent1
    )

    # CCPQ 3 (linked to bex4): Active, Late (18 days old, Threshold is 7)
    CCPQ.objects.create(
        numero_ccpq="CCPQ-2026-003",
        bex=bex4,
        date_depot=days_ago(18).date(),
        statut=CCPQ.StatutCCPQ.EN_ANALYSE,
        agent_createur=agent1
    )

    # CCPQ 4 (linked to bex5): Active, In Time (3 days old)
    CCPQ.objects.create(
        numero_ccpq="CCPQ-2026-004",
        bex=bex5,
        date_depot=days_ago(3).date(),
        statut=CCPQ.StatutCCPQ.NON_DEMARRE,
        agent_createur=agent1
    )

    # CCPQ 5 (Independent): Completed this week (4 days duration)
    CCPQ.objects.create(
        numero_ccpq="CCPQ-2026-005",
        date_depot=days_ago(9).date(),
        date_resultat=days_ago(5).date(),
        resultat="Conforme et enregistré.",
        statut=CCPQ.StatutCCPQ.APPROUVE,
        agent_createur=agent1
    )

    print("Dossiers CCPQ créés.")
    print("Peuplement terminé avec succès !")

if __name__ == "__main__":
    populate_data()

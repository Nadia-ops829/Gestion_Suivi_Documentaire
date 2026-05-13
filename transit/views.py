import pandas as pd
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated

from .models import BEX, BEXItem, Conteneur, ADI, CCPQ, DocumentTransit
from .serializers import (
    BEXSerializer, BEXDossierCompletSerializer, 
    DocumentTransitSerializer, ADISerializer, CCPQSerializer
)
from users.models import User
from users.permissions import get_visible_objects, CanManageTransit, IsChefService

class BEXViewSet(viewsets.ModelViewSet):
    queryset = BEX.objects.all()
    serializer_class = BEXSerializer
    permission_classes = [IsAuthenticated, CanManageTransit]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['type_bex', 'statut']
    search_fields = ['numero_bex', 'fournisseur']

    def get_queryset(self):
        # Filtre automatique selon le rôle (Agent ne voit que les siens)
        return get_visible_objects(self.request.user, BEX.objects.all(), creator_field='agent_createur')

    def perform_create(self, serializer):
        serializer.save(agent_createur=self.request.user)

    @action(detail=True, methods=['get'], url_path='dossier-complet')
    def dossier_complet(self, request, pk=None):
        """Récupère toutes les infos liées au BEX (Items, Docs, ADIs, CCPQs)"""
        bex = self.get_object()
        serializer = BEXDossierCompletSerializer(bex)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='upload-document', parser_classes=[MultiPartParser, FormParser])
    def upload_document(self, request, pk=None):
        """Upload d'un document rattaché au BEX"""
        bex = self.get_object()
        data = request.data.copy()
        data['bex'] = bex.id
        data['agent_createur'] = request.user.id
        serializer = DocumentTransitSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsChefService])
    def valider(self, request, pk=None):
        """Action Chef de Service pour valider le dossier"""
        bex = self.get_object()
        bex.statut = BEX.StatutBex.VALIDE
        bex.save()
        return Response({"status": "Dossier validé avec succès"})

    @action(detail=False, methods=['post'], url_path='import-excel', parser_classes=[MultiPartParser])
    def import_excel(self, request):
        """Importation Excel flexible pour le format Proforma Maritime"""
        file = request.FILES.get('file')
        if not file: return Response({"error": "Fichier manquant"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            df = pd.read_excel(file)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            created_count = 0
            with transaction.atomic():
                col_id = next((c for c in ['FACTURES', 'N° BEX', 'BEX', 'N°'] if c in df.columns), None)
                if not col_id:
                    return Response({"error": f"Colonnes non reconnues. Attendu 'FACTURES' ou 'N° BEX'."}, status=status.HTTP_400_BAD_REQUEST)

                for val_id, group in df.groupby(col_id):
                    if pd.isna(val_id): continue
                    bex, _ = BEX.objects.get_or_create(
                        numero_bex=str(val_id),
                        defaults={'fournisseur': 'Import Auto', 'agent_createur': request.user}
                    )
                    for _, row in group.iterrows():
                        BEXItem.objects.create(
                            bex=bex,
                            numero_conteneur='N/A',
                            designation_produit=f"Produit Facture {val_id}",
                            quantite=row.get('QUANTITES', 0) or row.get('QUANTITÉ', 0),
                            facture_fcfa=row.get('COUT', 0) or 0
                        )
                    created_count += 1
            return Response({"message": f"Import réussi: {created_count} dossiers"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ADIViewSet(viewsets.ModelViewSet):
    queryset = ADI.objects.all()
    serializer_class = ADISerializer
    permission_classes = [IsAuthenticated, CanManageTransit]

    def perform_create(self, serializer):
        serializer.save(agent_createur=self.request.user)

    @action(detail=False, methods=['post'], url_path='import-excel', parser_classes=[MultiPartParser])
    def import_excel(self, request):
        file = request.FILES.get('file')
        if not file: return Response({"error": "Fichier manquant"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            df = pd.read_excel(file)
            # Normalisation des colonnes : on enlève les espaces et on met en majuscules
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # Gestion des cellules fusionnées (dates qui ne sont pas répétées sur chaque ligne)
            df = df.ffill()
            
            col_target = next((c for c in ['FACTURES', 'N° ADI', 'ADI', 'N°'] if c in df.columns), None)
            
            created_count = 0
            with transaction.atomic():
                for _, row in df.iterrows():
                    val = row.get(col_target)
                    if pd.isna(val) or str(val).strip() == "": continue
                    num = str(val).strip()
                    
                    # Nettoyage du coût (gestion du séparateur décimal virgule)
                    cout_val = row.get('COUT', 0)
                    if isinstance(cout_val, str):
                        cout_val = cout_val.replace(',', '.').replace(' ', '')
                    
                    try:
                        cout_val = float(cout_val)
                    except (ValueError, TypeError):
                        cout_val = 0

                    # Nettoyage des dates pour éviter les erreurs NaT de pandas
                    def clean_date(val):
                        if pd.isna(val) or val is pd.NaT:
                            return None
                        return val

                    if not ADI.objects.filter(numero_adi=num).exists():
                        ADI.objects.create(
                            numero_adi=num,
                            factures=str(row.get('FACTURES', '')),
                            nb_items=int(row.get('ITEMS', 0) or 0),
                            quantite=int(row.get('QUANTITES', 0) or 0),
                            asi=int(row.get('ASI', 0) or 0),
                            cout=cout_val,
                            date_depot=clean_date(row.get('DATE DEPOT')) or clean_date(row.get('DATE')),
                            date_reception=clean_date(row.get('DATE RECEPTION')),
                            statut='EN_ATTENTE',
                            agent_createur=request.user
                        )
                        created_count += 1
            return Response({"message": f"Import réussi: {created_count} ADI"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CCPQViewSet(viewsets.ModelViewSet):
    queryset = CCPQ.objects.all()
    serializer_class = CCPQSerializer
    permission_classes = [IsAuthenticated, CanManageTransit]

    def perform_create(self, serializer):
        serializer.save(agent_createur=self.request.user)

    @action(detail=False, methods=['post'], url_path='import-excel', parser_classes=[MultiPartParser])
    def import_excel(self, request):
        file = request.FILES.get('file')
        try:
            df = pd.read_excel(file)
            df.columns = [str(c).strip().upper() for c in df.columns]
            col_target = next((c for c in ['FACTURES', 'N° CCPQ', 'CCPQ', 'N°'] if c in df.columns), None)
            
            created_count = 0
            with transaction.atomic():
                for _, row in df.iterrows():
                    val = row.get(col_target)
                    if pd.isna(val) or str(val).strip() == "": continue
                    num = str(val).strip()
                    if not CCPQ.objects.filter(numero_ccpq=num).exists():
                        CCPQ.objects.create(
                            numero_ccpq=num, 
                            date_depot=row.get('DATE DEPOT'), 
                            statut='NON_DEMARRE',
                            agent_createur=request.user
                        )
                        created_count += 1
            return Response({"message": f"Import réussi: {created_count} CCPQ"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

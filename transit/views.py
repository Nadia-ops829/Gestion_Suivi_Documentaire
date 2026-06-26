import pandas as pd
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated

from .models import BEX, BEXItem, Conteneur, ADI, CCPQ, DocumentTransit, FactureProforma
from .serializers import (
    BEXSerializer, BEXDossierCompletSerializer, 
    DocumentTransitSerializer, ADISerializer, CCPQSerializer, FactureProformaSerializer
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
        """Importation Excel flexible pour le format BEX"""
        file = request.FILES.get('file')
        if not file: return Response({"error": "Fichier manquant"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            df_raw = pd.read_excel(file, header=None)
            
            bex_number = None
            date_depart = None
            date_arrivee = None
            header_row_idx = 0
            
            # Extract header info (BEX, DATE DEPART, DATE ARRIVEE)
            for i, row in df_raw.head(10).iterrows():
                row_str = ' '.join(str(x).upper() for x in row.values)
                if 'BEX' in row_str and not bex_number:
                    # Find the cell containing the BEX number
                    for val in row.values:
                        if pd.notna(val) and str(val).strip().upper() != 'BEX':
                            bex_number = str(val).strip()
                            break
                if 'DATE DEPART' in row_str and not date_depart:
                    for val in row.values:
                        if pd.notna(val) and str(val).strip().upper() != 'DATE DEPART':
                            date_depart = val
                            break
                if 'DATE ARRIVEE' in row_str and not date_arrivee:
                    for val in row.values:
                        if pd.notna(val) and str(val).strip().upper() != 'DATE ARRIVEE':
                            date_arrivee = val
                            break
                if 'NUMERO FACTURE' in row_str or 'NUMÉRO FACTURE' in row_str:
                    header_row_idx = i
                    
            if not bex_number:
                # Fallback: maybe it's the old format where BEX is a column
                df = pd.read_excel(file)
                df.columns = [str(c).strip().upper() for c in df.columns]
                col_id = next((c for c in ['FACTURES', 'N° BEX', 'BEX', 'N°'] if c in df.columns), None)
                if not col_id:
                    return Response({"error": "Numéro BEX introuvable dans le fichier."}, status=status.HTTP_400_BAD_REQUEST)
                # ... fall back to old logic (we can just implement the new logic primarily)
            
            # Clean dates
            def clean_date(val):
                if pd.isna(val) or val is pd.NaT: return None
                return val

            # Create or get BEX
            if bex_number:
                bex, created = BEX.objects.get_or_create(
                    numero_bex=bex_number,
                    defaults={
                        'fournisseur': 'Import', 
                        'agent_createur': request.user,
                        'date_depart': clean_date(date_depart),
                        'date_arrivee': clean_date(date_arrivee)
                    }
                )
                if not created:
                    if clean_date(date_depart): bex.date_depart = clean_date(date_depart)
                    if clean_date(date_arrivee): bex.date_arrivee = clean_date(date_arrivee)
                    bex.save()

                # Process items
                df = df_raw.iloc[header_row_idx+1:].copy()
                df.columns = [str(c).strip().upper() for c in df_raw.iloc[header_row_idx]]
                df = df.dropna(how='all')
                
                col_facture = next((c for c in df.columns if 'FACTURE' in c), None)
                col_adi = next((c for c in df.columns if 'ADI' in c), None)
                col_asi = next((c for c in df.columns if 'ASI' in c), None)
                col_sylvie = next((c for c in df.columns if 'SYLVIE' in c), None)
                col_doc = next((c for c in df.columns if 'DOCUMENT' in c), None)
                col_statut = next((c for c in df.columns if 'STATUT' in c), None)
                
                item_count = 0
                with transaction.atomic():
                    # Optionnel: On peut vider les anciens items ou juste rajouter
                    for _, row in df.iterrows():
                        facture_val = str(row.get(col_facture)).strip() if col_facture and not pd.isna(row.get(col_facture)) else ""
                        if not facture_val: continue
                        
                        adi_val = str(row.get(col_adi)).strip() if col_adi and not pd.isna(row.get(col_adi)) else ""
                        asi_val = str(row.get(col_asi)).strip() if col_asi and not pd.isna(row.get(col_asi)) else ""
                        sylvie_val = str(row.get(col_sylvie)).strip() if col_sylvie and not pd.isna(row.get(col_sylvie)) else ""
                        doc_val = str(row.get(col_doc)).strip() if col_doc and not pd.isna(row.get(col_doc)) else ""
                        statut_val = str(row.get(col_statut)).strip() if col_statut and not pd.isna(row.get(col_statut)) else ""
                        
                        # Use get_or_create to avoid duplicates if re-importing
                        BEXItem.objects.get_or_create(
                            bex=bex,
                            numero_facture=facture_val,
                            defaults={
                                'adi': adi_val,
                                'asi': asi_val,
                                'numero_sylvie': sylvie_val,
                                'document': doc_val,
                                'statut_item': statut_val,
                                'designation_produit': f"Facture {facture_val}"
                            }
                        )
                        item_count += 1
                        
                return Response({"message": f"Import BEX {bex_number} réussi avec {item_count} lignes factures."}, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": "Format non reconnu."}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            import traceback
            print(traceback.format_exc())
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
        if not file: return Response({"error": "Fichier manquant"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Read without headers first to dynamically find the header row
            df_raw = pd.read_excel(file, header=None)
            header_row_idx = 0
            for i, row in df_raw.iterrows():
                row_str = ' '.join(str(x).upper() for x in row.values)
                if 'DCQ' in row_str or 'FOB EURO' in row_str or 'SYLVIE' in row_str:
                    header_row_idx = i
                    break
            
            # Set columns
            df = df_raw.iloc[header_row_idx+1:].copy()
            df.columns = [str(c).strip().upper() for c in df_raw.iloc[header_row_idx]]
            
            # Clean dataframe (remove empty rows)
            df = df.dropna(how='all')

            col_target = next((c for c in df.columns if 'DCQ' in c or 'CCPQ' in c and 'SYLVIE' not in c), None)
            if not col_target:
                return Response({"error": "Colonne N°DCQ ou N°CCPQ introuvable dans le fichier."}, status=status.HTTP_400_BAD_REQUEST)
            
            col_bex = next((c for c in df.columns if 'BEX' in c), None)
            col_sylvie = next((c for c in df.columns if 'SYLVIE' in c), None)
            col_euro = next((c for c in df.columns if 'EURO' in c), None)
            col_fcfa = next((c for c in df.columns if 'FCFA' in c), None)

            created_count = 0
            updated_count = 0
            with transaction.atomic():
                for _, row in df.iterrows():
                    val = row.get(col_target)
                    if pd.isna(val) or str(val).strip() == "": continue
                    num = str(val).strip()

                    # Find and link BEX if possible
                    bex_obj = None
                    if col_bex and not pd.isna(row.get(col_bex)):
                        bex_val = str(row.get(col_bex)).strip()
                        # Si le BEX correspond exactement à un numéro en base
                        bex_obj = BEX.objects.filter(numero_bex=bex_val).first()

                    # Clean decimal values
                    def clean_decimal(val):
                        if pd.isna(val): return 0
                        val_str = str(val).replace(',', '.').replace(' ', '').replace('\xa0', '')
                        try: return float(val_str)
                        except: return 0

                    euro_val = clean_decimal(row.get(col_euro)) if col_euro else 0
                    fcfa_val = clean_decimal(row.get(col_fcfa)) if col_fcfa else 0
                    sylvie_val = str(row.get(col_sylvie)).strip() if col_sylvie and not pd.isna(row.get(col_sylvie)) else ""

                    ccpq, created = CCPQ.objects.get_or_create(
                        numero_ccpq=num,
                        defaults={
                            'bex': bex_obj,
                            'numero_sylvie': sylvie_val,
                            'fob_euro': euro_val,
                            'fob_fcfa': fcfa_val,
                            'statut': 'NON_DEMARRE',
                            'agent_createur': request.user
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        # Update existing CCPQ
                        ccpq.numero_sylvie = sylvie_val
                        ccpq.fob_euro = euro_val
                        ccpq.fob_fcfa = fcfa_val
                        if bex_obj and not ccpq.bex:
                            ccpq.bex = bex_obj
                        ccpq.save()
                        updated_count += 1

            return Response({"message": f"Import réussi: {created_count} créés, {updated_count} mis à jour."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class FactureProformaViewSet(viewsets.ModelViewSet):
    queryset = FactureProforma.objects.all()
    serializer_class = FactureProformaSerializer
    permission_classes = [IsAuthenticated, IsChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['reference']

    def perform_create(self, serializer):
        serializer.save(agent_createur=self.request.user)

    @action(detail=False, methods=['post'], url_path='import-excel', parser_classes=[MultiPartParser])
    def import_excel(self, request):
        """Importation Excel pour le suivi des factures et pro-formas"""
        file = request.FILES.get('file')
        if not file: return Response({"error": "Fichier manquant"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            df_raw = pd.read_excel(file, header=None)
            header_row_idx = 0
            for i, row in df_raw.iterrows():
                row_str = ' '.join(str(x).upper() for x in row.values)
                if 'RÉF' in row_str or 'REF' in row_str or 'FACTURE' in row_str:
                    header_row_idx = i
                    break
            
            df = df_raw.iloc[header_row_idx+1:].copy()
            df.columns = [str(c).strip().upper() for c in df_raw.iloc[header_row_idx]]
            df = df.dropna(how='all')

            created_count = 0
            updated_count = 0
            with transaction.atomic():
                for _, row in df.iterrows():
                    col_ref = next((c for c in df.columns if 'RÉF' in c or 'REF' in c or 'FACTURE' in c and 'COUT' not in c and 'COÛT' not in c), None)
                    col_nb_item = next((c for c in df.columns if 'NOMBRE' in c and 'ITEM' in c), None)
                    col_qte = next((c for c in df.columns if 'QUANTIT' in c), None)
                    col_asi = next((c for c in df.columns if 'ASI' in c), None)
                    col_adi = next((c for c in df.columns if 'ADI' in c), None)
                    col_cout = next((c for c in df.columns if 'COUT' in c or 'COÛT' in c), None)

                    if not col_ref: continue
                    val_ref = row.get(col_ref)
                    if pd.isna(val_ref) or str(val_ref).strip() == "": continue
                    
                    ref = str(val_ref).strip()

                    def safe_int(val):
                        if pd.isna(val): return 0
                        try: return int(float(str(val).replace(' ', '')))
                        except: return 0

                    def safe_float(val):
                        if pd.isna(val): return 0
                        try: return float(str(val).replace(',', '.').replace(' ', ''))
                        except: return 0

                    nb_item = safe_int(row.get(col_nb_item)) if col_nb_item else 0
                    qte = safe_int(row.get(col_qte)) if col_qte else 0
                    asi = safe_int(row.get(col_asi)) if col_asi else 0
                    adi = safe_int(row.get(col_adi)) if col_adi else 0
                    cout = safe_float(row.get(col_cout)) if col_cout else 0

                    obj, created = FactureProforma.objects.update_or_create(
                        reference=ref,
                        defaults={
                            'nombre_item': nb_item,
                            'quantite_produits': qte,
                            'items_asi': asi,
                            'items_adi': adi,
                            'cout_facture': cout,
                            'agent_createur': request.user
                        }
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

            return Response({
                "message": f"Import réussi: {created_count} factures créées, {updated_count} mises à jour."
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

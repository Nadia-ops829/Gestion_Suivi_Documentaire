import datetime
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from transit.models import BEX, ADI, CCPQ, Conteneur, DocumentTransit
from users.models import User

# Thresholds in days
BEX_THRESHOLD = 15
ADI_THRESHOLD = 5
CCPQ_THRESHOLD = 7

def get_bex_completion_date(bex):
    """
    Tries to find the official completion date of a BEX dossier.
    Matches the upload of Liquidation (Dédouané) or REC165 (Prêt pour réception).
    """
    doc = bex.documents.filter(
        type_document__in=['LIQUIDATION', 'REC165']
    ).order_by('date_upload').first()
    if doc:
        return doc.date_upload
    if bex.date_reception_rsi:
        return bex.date_reception_rsi
    if bex.date_pointage_pharmacien:
        return bex.date_pointage_pharmacien
    return None

def get_bex_processing_days(bex):
    """
    Calculates the total processing days for a BEX.
    If completed, uses the completion date. If active, uses timezone.now().
    """
    if bex.statut in ['DEDOUANE', 'PRET_RECEPTION']:
        comp_date = get_bex_completion_date(bex)
        if comp_date:
            return max(0, (comp_date - bex.date_creation).days)
    return max(0, (timezone.now() - bex.date_creation).days)

def get_adi_processing_days(adi):
    """
    Calculates the total processing days for an ADI (using DateField date_depot & date_reception).
    """
    depot = adi.date_depot
    if not depot:
        if adi.bex:
            depot = adi.bex.date_creation.date()
        else:
            return 0
            
    if adi.statut in ['VALIDE', 'REJETE'] and adi.date_reception:
        return max(0, (adi.date_reception - depot).days)
        
    return max(0, (timezone.now().date() - depot).days)

def get_ccpq_processing_days(ccpq):
    """
    Calculates the total processing days for a CCPQ (using DateField date_depot & date_resultat).
    """
    depot = ccpq.date_depot
    if not depot:
        if ccpq.bex:
            depot = ccpq.bex.date_creation.date()
        else:
            return 0
            
    if ccpq.statut in ['APPROUVE', 'REJETE'] and ccpq.date_resultat:
        return max(0, (ccpq.date_resultat - depot).days)
        
    return max(0, (timezone.now().date() - depot).days)

def calculate_dashboard_metrics(agent_id=None, periode=None, type_dossier=None):
    """
    Aggregates all core KPIs and chart metrics for the dashboard.
    Filters:
      - agent_id: only dossiers created by the specified transit agent.
      - periode: 'semaine' (last 7 days), 'mois' (last 30 days), 'trimestre' (last 90 days).
      - type_dossier: 'BEX', 'ADI', 'CCPQ', or 'CONTENEUR'.
    """
    now = timezone.now()
    
    # 1. Base Querysets
    bex_qs = BEX.objects.all()
    adi_qs = ADI.objects.all()
    ccpq_qs = CCPQ.objects.all()
    conteneur_qs = Conteneur.objects.all()
    
    # 2. Apply Agent Filter
    if agent_id:
        bex_qs = bex_qs.filter(agent_createur_id=agent_id)
        adi_qs = adi_qs.filter(agent_createur_id=agent_id)
        ccpq_qs = ccpq_qs.filter(agent_createur_id=agent_id)
        conteneur_qs = conteneur_qs.filter(bex__agent_createur_id=agent_id)
        
    # 3. Apply Period Filter
    start_date = None
    if periode:
        if periode == 'semaine':
            start_date = now - timedelta(days=7)
        elif periode == 'mois':
            start_date = now - timedelta(days=30)
        elif periode == 'trimestre':
            start_date = now - timedelta(days=90)
            
        if start_date:
            bex_qs = bex_qs.filter(date_creation__gte=start_date)
            adi_qs = adi_qs.filter(date_depot__gte=start_date.date())
            ccpq_qs = ccpq_qs.filter(date_depot__gte=start_date.date())
            conteneur_qs = conteneur_qs.filter(bex__date_creation__gte=start_date)

    # 4. Count Active Dossiers (Uncompleted dossiers count)
    active_bex_count = bex_qs.exclude(statut__in=['DEDOUANE', 'PRET_RECEPTION']).count()
    active_adi_count = adi_qs.exclude(statut__in=['VALIDE', 'REJETE']).count()
    active_ccpq_count = ccpq_qs.exclude(statut__in=['APPROUVE', 'REJETE']).count()
    active_conteneur_count = conteneur_qs.exclude(bex__statut__in=['DEDOUANE', 'PRET_RECEPTION']).count()
    
    active_counts = {
        'BEX': active_bex_count,
        'ADI': active_adi_count,
        'CCPQ': active_ccpq_count,
        'Conteneur': active_conteneur_count
    }
    
    # Total Active Dossiers based on type_dossier filter
    total_active_dossiers = 0
    if type_dossier:
        td_upper = type_dossier.upper()
        if td_upper == 'BEX':
            total_active_dossiers = active_bex_count
        elif td_upper == 'ADI':
            total_active_dossiers = active_adi_count
        elif td_upper == 'CCPQ':
            total_active_dossiers = active_ccpq_count
        elif td_upper == 'CONTENEUR':
            total_active_dossiers = active_conteneur_count
    else:
        total_active_dossiers = active_bex_count + active_adi_count + active_ccpq_count
        
    # 5. Overdue / Blocked Dossiers (Dossiers dépassant le délai)
    blocked_list = []
    
    # Check BEX
    active_bex = bex_qs.exclude(statut__in=['DEDOUANE', 'PRET_RECEPTION']).select_related('agent_createur')
    for bex in active_bex:
        days = get_bex_processing_days(bex)
        is_blocked = bex.statut == 'BLOQUE' or days > BEX_THRESHOLD
        if is_blocked:
            delay_days = max(0, days - BEX_THRESHOLD) if bex.statut != 'BLOQUE' else days
            blocked_list.append({
                'id': bex.id,
                'numero': bex.numero_bex,
                'type': 'BEX',
                'statut': bex.statut,
                'date_depot_creation': bex.date_creation.strftime('%Y-%m-%d'),
                'agent_responsable': bex.agent_createur.username if bex.agent_createur else 'N/A',
                'jours_retard': delay_days,
                'seuil_limite': BEX_THRESHOLD
            })
            
    # Check ADI
    active_adi = adi_qs.exclude(statut__in=['VALIDE', 'REJETE']).select_related('agent_createur')
    for adi in active_adi:
        days = get_adi_processing_days(adi)
        if days > ADI_THRESHOLD:
            blocked_list.append({
                'id': adi.id,
                'numero': adi.numero_adi,
                'type': 'ADI',
                'statut': adi.statut,
                'date_depot_creation': adi.date_depot.strftime('%Y-%m-%d') if adi.date_depot else 'N/A',
                'agent_responsable': adi.agent_createur.username if adi.agent_createur else 'N/A',
                'jours_retard': days - ADI_THRESHOLD,
                'seuil_limite': ADI_THRESHOLD
            })
            
    # Check CCPQ
    active_ccpq = ccpq_qs.exclude(statut__in=['APPROUVE', 'REJETE']).select_related('agent_createur')
    for ccpq in active_ccpq:
        days = get_ccpq_processing_days(ccpq)
        if days > CCPQ_THRESHOLD:
            blocked_list.append({
                'id': ccpq.id,
                'numero': ccpq.numero_ccpq,
                'type': 'CCPQ',
                'statut': ccpq.statut,
                'date_depot_creation': ccpq.date_depot.strftime('%Y-%m-%d') if ccpq.date_depot else 'N/A',
                'agent_responsable': ccpq.agent_createur.username if ccpq.agent_createur else 'N/A',
                'jours_retard': days - CCPQ_THRESHOLD,
                'seuil_limite': CCPQ_THRESHOLD
            })
            
    # Filter blocked_list by type_dossier if requested
    if type_dossier:
        td_upper = type_dossier.upper()
        if td_upper == 'CONTENEUR':
            blocked_list = [item for item in blocked_list if item['type'] == 'BEX']
        else:
            blocked_list = [item for item in blocked_list if item['type'] == td_upper]
            
    blocked_count = len(blocked_list)
    
    # 6. Average Processing Time (Délai moyen de traitement ce mois)
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # BEX completed this month
    completed_bex = bex_qs.filter(statut__in=['DEDOUANE', 'PRET_RECEPTION'])
    bex_durations = []
    for bex in completed_bex:
        comp_date = get_bex_completion_date(bex)
        if comp_date and comp_date >= first_day_of_month:
            dur = max(0, (comp_date - bex.date_creation).days)
            bex_durations.append(dur)
            
    # ADIs completed this month
    completed_adis = adi_qs.filter(
        statut__in=['VALIDE', 'REJETE'],
        date_reception__gte=first_day_of_month.date()
    )
    adi_durations = []
    for adi in completed_adis:
        dur = get_adi_processing_days(adi)
        adi_durations.append(dur)
        
    # CCPQs completed this month
    completed_ccpqs = ccpq_qs.filter(
        statut__in=['APPROUVE', 'REJETE'],
        date_resultat__gte=first_day_of_month.date()
    )
    ccpq_durations = []
    for ccpq in completed_ccpqs:
        dur = get_ccpq_processing_days(ccpq)
        ccpq_durations.append(dur)
        
    avg_bex = sum(bex_durations) / len(bex_durations) if bex_durations else 0.0
    avg_adi = sum(adi_durations) / len(adi_durations) if adi_durations else 0.0
    avg_ccpq = sum(ccpq_durations) / len(ccpq_durations) if ccpq_durations else 0.0
    
    avg_delays = {
        'BEX': round(avg_bex, 1),
        'ADI': round(avg_adi, 1),
        'CCPQ': round(avg_ccpq, 1)
    }
    
    # 7. Validation Rate (Taux de validation ce mois)
    total_completed_this_month = len(bex_durations) + len(adi_durations) + len(ccpq_durations)
    in_delay_completed_this_month = (
        sum(1 for d in bex_durations if d <= BEX_THRESHOLD) +
        sum(1 for d in adi_durations if d <= ADI_THRESHOLD) +
        sum(1 for d in ccpq_durations if d <= CCPQ_THRESHOLD)
    )
    
    if total_completed_this_month > 0:
        validation_rate = round((in_delay_completed_this_month / total_completed_this_month) * 100, 1)
    else:
        validation_rate = 100.0  # Default to 100.0% if no activity yet
        
    # 8. Chart 1: Grouped Bars (Nombre de dossiers traités par mois et par type)
    # Calculated for the last 6 months
    chart_grouped_bars = []
    MONTHS_FR = {
        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril', 5: 'Mai', 6: 'Juin',
        7: 'Juillet', 8: 'Août', 9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    }
    
    for i in range(5, -1, -1):
        target_month_date = now - timedelta(days=i * 30)
        m_num = target_month_date.month
        y_num = target_month_date.year
        m_name = MONTHS_FR[m_num]
        
        m_start = datetime.datetime(y_num, m_num, 1, tzinfo=timezone.get_current_timezone())
        if m_num == 12:
            m_end = datetime.datetime(y_num + 1, 1, 1, tzinfo=timezone.get_current_timezone())
        else:
            m_end = datetime.datetime(y_num, m_num + 1, 1, tzinfo=timezone.get_current_timezone())
            
        # BEX completed in month
        bex_cnt = 0
        bex_comp = BEX.objects.filter(statut__in=['DEDOUANE', 'PRET_RECEPTION'])
        if agent_id:
            bex_comp = bex_comp.filter(agent_createur_id=agent_id)
        for bex in bex_comp:
            c_date = get_bex_completion_date(bex)
            if c_date and m_start <= c_date < m_end:
                bex_cnt += 1
                
        # ADI completed in month
        adi_comp = ADI.objects.filter(statut__in=['VALIDE', 'REJETE'], date_reception__year=y_num, date_reception__month=m_num)
        if agent_id:
            adi_comp = adi_comp.filter(agent_createur_id=agent_id)
        adi_cnt = adi_comp.count()
        
        # CCPQ completed in month
        ccpq_comp = CCPQ.objects.filter(statut__in=['APPROUVE', 'REJETE'], date_resultat__year=y_num, date_resultat__month=m_num)
        if agent_id:
            ccpq_comp = ccpq_comp.filter(agent_createur_id=agent_id)
        ccpq_cnt = ccpq_comp.count()
        
        chart_grouped_bars.append({
            'month': f"{m_name} {y_num}",
            'BEX': bex_cnt,
            'ADI': adi_cnt,
            'CCPQ': ccpq_cnt
        })

    # 9. Chart 2: Camembert / Pie (Répartition des causes de retards: ADI, CCPQ, Douane, Autre)
    cause_counts = {'ADI': 0, 'CCPQ': 0, 'Douane': 0, 'Autre': 0}
    
    # We trace why current overdue items are late
    for item in blocked_list:
        if item['type'] == 'ADI':
            cause_counts['ADI'] += 1
        elif item['type'] == 'CCPQ':
            cause_counts['CCPQ'] += 1
        elif item['type'] == 'BEX':
            bex_obj = BEX.objects.get(id=item['id'])
            if bex_obj.statut == 'BLOQUE' or bex_obj.statut_douanier not in ['En attente', 'Dédouané']:
                cause_counts['Douane'] += 1
            else:
                has_adi_issue = bex_obj.adis.exclude(statut='VALIDE').exists()
                has_ccpq_issue = bex_obj.ccpqs.exclude(statut='APPROUVE').exists()
                if has_adi_issue:
                    cause_counts['ADI'] += 1
                elif has_ccpq_issue:
                    cause_counts['CCPQ'] += 1
                else:
                    cause_counts['Autre'] += 1
                    
    chart_pie = [
        {'label': 'Retards ADI', 'value': cause_counts['ADI']},
        {'label': 'Retards CCPQ', 'value': cause_counts['CCPQ']},
        {'label': 'Retards Douane', 'value': cause_counts['Douane']},
        {'label': 'Autres Causes', 'value': cause_counts['Autre']}
    ]
    
    # 10. Chart 3: Trend Curve (Évolution des délais de traitement semaine par semaine)
    chart_trend = []
    current_date = now
    for w in range(7, -1, -1):
        w_start = current_date - timedelta(days=w * 7 + 7)
        w_end = current_date - timedelta(days=w * 7)
        
        w_durations = []
        
        # BEX completed in week
        bex_comp = BEX.objects.filter(statut__in=['DEDOUANE', 'PRET_RECEPTION'])
        if agent_id:
            bex_comp = bex_comp.filter(agent_createur_id=agent_id)
        for bex in bex_comp:
            c_date = get_bex_completion_date(bex)
            if c_date and w_start <= c_date < w_end:
                w_durations.append(max(0, (c_date - bex.date_creation).days))
                
        # ADIs completed in week
        adi_comp = ADI.objects.filter(statut__in=['VALIDE', 'REJETE'], date_reception__range=[w_start.date(), w_end.date()])
        if agent_id:
            adi_comp = adi_comp.filter(agent_createur_id=agent_id)
        for adi in adi_comp:
            w_durations.append(get_adi_processing_days(adi))
            
        # CCPQs completed in week
        ccpq_comp = CCPQ.objects.filter(statut__in=['APPROUVE', 'REJETE'], date_resultat__range=[w_start.date(), w_end.date()])
        if agent_id:
            ccpq_comp = ccpq_comp.filter(agent_createur_id=agent_id)
        for ccpq in ccpq_comp:
            w_durations.append(get_ccpq_processing_days(ccpq))
            
        avg_w = sum(w_durations) / len(w_durations) if w_durations else 0.0
        week_num = w_end.isocalendar()[1]
        
        chart_trend.append({
            'week': f"Semaine {week_num}",
            'avg_days': round(avg_w, 1)
        })

    # Sort late dossiers table by days of delay
    late_dossiers_table = sorted(blocked_list, key=lambda x: x['jours_retard'], reverse=True)[:10]

    # Compile filter choices metadata
    available_agents = User.objects.filter(role=User.Role.AGENT).values('id', 'username', 'first_name', 'last_name')
    agents_list = [{'id': u['id'], 'name': f"{u['first_name']} {u['last_name']} ({u['username']})"} for u in available_agents]

    return {
        'active_counts': active_counts,
        'total_active_dossiers': total_active_dossiers,
        'blocked_count': blocked_count,
        'avg_delays': avg_delays,
        'validation_rate': validation_rate,
        'charts': {
            'grouped_bars': chart_grouped_bars,
            'pie_causes': chart_pie,
            'trend_weeks': chart_trend,
        },
        'late_dossiers_table': late_dossiers_table,
        'filters_metadata': {
            'agents': agents_list,
            'types': ['BEX', 'ADI', 'CCPQ', 'CONTENEUR'],
            'periods': [
                {'key': 'semaine', 'label': 'Semaine'},
                {'key': 'mois', 'label': 'Mois'},
                {'key': 'trimestre', 'label': 'Trimestre'}
            ]
        }
    }

def generate_excel_report(agent_id=None, periode=None, type_dossier=None):
    """
    Generates a high-quality in-memory Excel file representing all dashboard metrics.
    Includes active dossier summaries, late dossiers list, and trend details.
    """
    import io
    import pandas as pd
    
    # Calculate real-time metrics
    metrics = calculate_dashboard_metrics(agent_id=agent_id, periode=periode, type_dossier=type_dossier)
    
    # Create byte buffer
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Global Metrics
        summary_data = {
            'Indicateur Clé': [
                'Total Dossiers Actifs (BEX + ADI + CCPQ)',
                'BEX Actifs (Non dédouanés)',
                'ADI Actifs (En attente / Soumis)',
                'CCPQ Actifs (Non démarrés / En analyse)',
                'Conteneurs Actifs (Suivi)',
                'Nombre total de dossiers en retard',
                'Taux de validation réglementaire (ce mois)',
                'Délai moyen de traitement - BEX (ce mois)',
                'Délai moyen de traitement - ADI (ce mois)',
                'Délai moyen de traitement - CCPQ (ce mois)'
            ],
            'Valeur': [
                metrics['total_active_dossiers'],
                metrics['active_counts']['BEX'],
                metrics['active_counts']['ADI'],
                metrics['active_counts']['CCPQ'],
                metrics['active_counts']['Conteneur'],
                metrics['blocked_count'],
                f"{metrics['validation_rate']}%",
                f"{metrics['avg_delays']['BEX']} jours",
                f"{metrics['avg_delays']['ADI']} jours",
                f"{metrics['avg_delays']['CCPQ']} jours"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Synthèse KPIs', index=False)
        
        # Sheet 2: Late Dossiers Table
        late_rows = []
        for d in metrics['late_dossiers_table']:
            late_rows.append({
                'N° Dossier': d['numero'],
                'Type de Dossier': d['type'],
                'Statut Actuel': d['statut'],
                'Date Dépôt / Création': d['date_depot_creation'],
                'Agent Responsable': d['agent_responsable'],
                'Jours de Retard constatés': d['jours_retard'],
                'Seuil SLA légal (jours)': d['seuil_limite']
            })
            
        if not late_rows:
            late_rows = [{'Message': 'Aucun dossier en retard ! Performance parfaite.'}]
            
        pd.DataFrame(late_rows).to_excel(writer, sheet_name='Dossiers en Retard', index=False)
        
        # Sheet 3: Monthly Statistics
        bar_data = []
        for x in metrics['charts']['grouped_bars']:
            bar_data.append({
                'Mois': x['month'],
                'Dossiers traités - BEX': x['BEX'],
                'Dossiers traités - ADI': x['ADI'],
                'Dossiers traités - CCPQ': x['CCPQ']
            })
        pd.DataFrame(bar_data).to_excel(writer, sheet_name='Historique Mensuel', index=False)

    output.seek(0)
    return output

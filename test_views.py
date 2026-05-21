import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_Suivi_Documentaire.settings')
django.setup()

from django.conf import settings as django_settings
django_settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from users.models import User

def test_endpoints():
    print("Démarrage du test d'intégration des APIs...")
    client = Client()

    # 1. Test without authentication (should return 403 Forbidden)
    res = client.get('/api/analytics/dashboard-data/')
    print(f"Test non-authentifié : Status Code = {res.status_code} (Attendu: 403)")
    assert res.status_code == 403

    # 2. Authenticate as agent1
    # We log in using django client login
    logged_in = client.login(username='agent1', password='agent123')
    print(f"Connexion en tant que agent1 : {logged_in} (Attendu: True)")
    assert logged_in

    # 3. Test Dashboard Data endpoint (Unfiltered)
    res = client.get('/api/analytics/dashboard-data/')
    print(f"Test /api/analytics/dashboard-data/ : Status Code = {res.status_code} (Attendu: 200)")
    assert res.status_code == 200
    
    data = res.json()
    print("\n--- Données KPI ---")
    print(f"Dossiers Actifs par type : {data['active_counts']}")
    print(f"Nombre total actifs : {data['total_active_dossiers']}")
    print(f"Dossiers Bloqués / Retard : {data['blocked_count']}")
    print(f"Délai moyen de traitement ce mois : {data['avg_delays']}")
    print(f"Taux de validation ce mois : {data['validation_rate']}%")

    print("\n--- Données Graphiques ---")
    print(f"Barres Groupées (Mois) : {data['charts']['grouped_bars']}")
    print(f"Causes de Retards (Camembert) : {data['charts']['pie_causes']}")
    print(f"Tendance Hebdomadaire (Courbe) : {data['charts']['trend_weeks']}")
    print(f"Tableau Dossiers en retard (Top 10 cliquable) : {len(data['late_dossiers_table'])} dossiers répertoriés")

    # 4. Test filtering by period
    res_filtered = client.get('/api/analytics/dashboard-data/?periode=semaine')
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.json()
    print(f"\nTest filtre periode=semaine (Total actifs filtré) : {data_filtered['total_active_dossiers']}")

    # 5. Test filtering by type_dossier
    res_type = client.get('/api/analytics/dashboard-data/?type_dossier=BEX')
    assert res_type.status_code == 200
    data_type = res_type.json()
    print(f"Test filtre type_dossier=BEX (Total actifs filtré BEX) : {data_type['total_active_dossiers']}")

    # 6. Test Power BI Embed endpoint
    res_pbi = client.get('/api/analytics/powerbi-embed/')
    print(f"\nTest /api/analytics/powerbi-embed/ : Status Code = {res_pbi.status_code} (Attendu: 200)")
    assert res_pbi.status_code == 200
    
    pbi_data = res_pbi.json()
    print(f"Rapport ID : {pbi_data['reportId']}")
    print(f"Embed URL : {pbi_data['embedUrl'][:70]}...")
    print(f"Embed Token : {pbi_data['accessToken'][:40]}...")
    print(f"Est une simulation / Mock : {pbi_data['is_mock']}")
    
    print("\nTous les tests d'intégration ont été exécutés avec SUCCÈS ! 🎉")

if __name__ == "__main__":
    test_endpoints()

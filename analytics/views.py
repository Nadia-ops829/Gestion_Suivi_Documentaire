import os
import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .dashboard_logic import calculate_dashboard_metrics

class DashboardDataAPIView(APIView):
    """
    API endpoint that aggregates statistics, KPIs, and chart data
    for the transit and document monitoring dashboard.
    Enforces Role-Based Security:
      - AGENT: Can ONLY view their own dossier statistics (forced filter).
      - CHEF_SERVICE / ADMIN: Can view global statistics and filter dynamically by agent.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from users.models import User
        
        agent_id = request.query_params.get('agent_id')
        periode = request.query_params.get('periode')
        type_dossier = request.query_params.get('type_dossier')
        
        # Enforce Row-Level Role Security:
        # Transit Agents can ONLY access their own data.
        if request.user.role == User.Role.AGENT:
            agent_id = request.user.id
        
        try:
            # Validate agent_id is an integer if provided
            if agent_id:
                agent_id = int(agent_id)
        except ValueError:
            return Response(
                {"error": "Le paramètre agent_id doit être un entier valide."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            metrics = calculate_dashboard_metrics(
                agent_id=agent_id,
                periode=periode,
                type_dossier=type_dossier
            )
            return Response(metrics, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            # Print traceback to Django logs for debugging
            print(traceback.format_exc())
            return Response(
                {"error": f"Une erreur interne s'est produite lors du calcul des indicateurs: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PowerBIEmbedAPIView(APIView):
    """
    API endpoint to obtain the Power BI Embedded configuration
    (Embed URL, Report ID, and Embed Token) for frontend integration.
    Falls back gracefully to a realistic mock configuration if Azure environment variables are not set.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Read Azure AD & Power BI configs from environment / Django settings
        client_id = os.environ.get('POWERBI_CLIENT_ID', getattr(settings, 'POWERBI_CLIENT_ID', None))
        client_secret = os.environ.get('POWERBI_CLIENT_SECRET', getattr(settings, 'POWERBI_CLIENT_SECRET', None))
        tenant_id = os.environ.get('POWERBI_TENANT_ID', getattr(settings, 'POWERBI_TENANT_ID', None))
        workspace_id = os.environ.get('POWERBI_WORKSPACE_ID', getattr(settings, 'POWERBI_WORKSPACE_ID', None))
        report_id = os.environ.get('POWERBI_REPORT_ID', getattr(settings, 'POWERBI_REPORT_ID', None))

        # Check if all required variables are set to execute the real embedding flow
        if all([client_id, client_secret, tenant_id, workspace_id, report_id]):
            try:
                # 1. Fetch Azure AD Access Token via Client Credentials flow
                token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
                token_data = {
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'scope': 'https://analysis.windows.net/powerbi/api/.default'
                }
                token_res = requests.post(token_url, data=token_data)
                
                if token_res.status_code != 200:
                    return Response(
                        {"error": "Impossible d'obtenir le token Azure AD d'authentification.", "details": token_res.json()},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                access_token = token_res.json().get('access_token')

                # 2. Get Report Embed URL from Power BI REST API
                report_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}"
                headers = {'Authorization': f"Bearer {access_token}"}
                report_res = requests.get(report_url, headers=headers)
                
                if report_res.status_code != 200:
                    return Response(
                        {"error": "Impossible de récupérer les métadonnées du rapport Power BI.", "details": report_res.json()},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                embed_url = report_res.json().get('embedUrl')

                # 3. Generate Embed Token
                token_req_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}/GenerateToken"
                token_req_data = {'accessLevel': 'View'}
                token_req_res = requests.post(token_req_url, headers=headers, json=token_req_data)
                
                if token_req_res.status_code != 200:
                    return Response(
                        {"error": "Impossible de générer le jeton d'intégration (Embed Token) Power BI.", "details": token_req_res.json()},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                embed_token = token_req_res.json().get('token')
                expiry = token_req_res.json().get('expiration')

                return Response({
                    'reportId': report_id,
                    'workspaceId': workspace_id,
                    'embedUrl': embed_url,
                    'accessToken': embed_token,
                    'expiry': expiry,
                    'is_mock': False
                }, status=status.HTTP_200_OK)

            except Exception as e:
                # Handle unexpected API calling errors gracefully and log them
                print(f"Error during Power BI Embedded API Call: {str(e)}")
                # We can fallback to mock if requested, or return error. Let's return error but offer a mock flag
                if request.query_params.get('fallback_mock') == 'true':
                    pass
                else:
                    return Response(
                        {"error": f"Erreur lors de la communication avec Azure/Power BI API: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

        # 4. Fallback to highly-detailed Mock embedding config
        # This makes it instantly possible for frontend developers to test powerbi-client library setup
        mock_report_id = report_id or "f68234ea-348e-49b0-9b34-8c812d1b09b5"
        mock_workspace_id = workspace_id or "c55123d4-221d-44a1-b844-301db5432ab8"
        
        # A realistic Power BI embedded iframe source URL
        mock_embed_url = (
            f"https://app.powerbi.com/reportEmbed?"
            f"reportId={mock_report_id}&"
            f"groupId={mock_workspace_id}&"
            f"config=eyJjbHVzdGVyVXJsIjoiaHR0cHM6Ly93YWJpLXdlc3QtdXMtcmVkaXJlY3QuYW5hbHlzaXMud2luZG93cy5uZXQvIn0%3d"
        )
        
        # Simulated base64 Power BI Embed token
        mock_token = (
            "MockEmbedToken_H4sIAAAAAAAEAC2Wx47EIBRF_2VqWkkiZ1ZpeggpggtMMyMIMgZlePv26exK3nrvV757D3-S2Lw5kC3M7s6j5mrc"
            "D0n1PshMlhC7g1c2-y1pQYgD6qM5gCjZz-qWzUqSExgA0bIf3D6n4F3dshcQD7tqD-d-0mF3fSnbZ723BwhnK_aGk1s2-2-V5D7rY0F"
            "tD-rZsn9T159S9tDmsd3bA322pG293W2fbdvsh9h577yG3jtnk7W0fWz7ZJtHj71y2G3rrE1t19r2sd33eWq7z9Lz1mMPvVfOOtuxZJ"
            "dHj7tqj33M20N7157mXfeR3j2p1v0h0b3T3Z2Z3W322KvzFnv0tNl973R3Z3bZ41pD-6yH9tDmvPVuw1457FpDa92Z2WXPpOzReQv22"
            "EvH3Rz7Xfbe1T7bY4-9dtiDPZuyZ5Oyx72zts8ee9270nknW-y90z55Nmv32Htnk8ded8l-yN7Xk_Ieb7LHzlvaZ2uzN7uPvXM2e-y9"
            "R03O-uxR5z4G9s6Z0pPOOz0Teyc_W_awZ4_t3XvssYfZ2W0bJmUPs2-YZ_P2sNnDnj22dzd7D_bsyexh9g3zbN7O1n0M6J3zbJg9zD55"
            "2LNn0pM9e2y71nv2tPe1D96GPHtnc9YeZt-wT7aH7Dzb3TntZ_Mwe2ezZ5-9tWFPZrNnsz-bPfsZMnsye-Ww2T2ZzZ7N-ezZ7M-ezR41"
            "u1tDZm8N2OyePdtv7-z/wAYAAA=="
        )

        future_expiry = (timezone.now() + timezone.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')

        return Response({
            'reportId': mock_report_id,
            'workspaceId': mock_workspace_id,
            'embedUrl': mock_embed_url,
            'accessToken': mock_token,
            'expiry': future_expiry,
            'is_mock': True,
            'message': (
                "Jeton d'intégration de démonstration généré. Configurez les variables d'environnement "
                "POWERBI_CLIENT_ID, POWERBI_CLIENT_SECRET, POWERBI_TENANT_ID, POWERBI_WORKSPACE_ID "
                "et POWERBI_REPORT_ID pour activer l'intégration réelle avec Microsoft Azure."
            )
        }, status=status.HTTP_200_OK)

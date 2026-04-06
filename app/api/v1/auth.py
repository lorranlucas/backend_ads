from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
import os
from app.services.meta import MetaService, GRAPH_API_VERSION
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
# Use env variable or default to the production domain (HTTP for local hosts testing)
REDIRECT_URI = os.getenv("META_REDIRECT_URI", "http://localhost:8000/api/v1/auth/meta/callback")
FRONTEND_ORIGIN = os.getenv("FRONTEND_URL", "http://localhost:8080")

@router.get("/meta/login")
async def meta_login():
    """Redirect user to Facebook OAuth dialog via Business Login."""
    # Usando scopes padrão para permitir selecionar VÁRIOS portfólios de uma vez
    scope = "ads_management,ads_read,business_management"
    url = (
        f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth?"
        f"client_id={META_APP_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={scope}"
    )
    return RedirectResponse(url)

@router.get("/meta/callback")
async def meta_callback(code: str = Query(None), error: str = Query(None)):
    """Handle the OAuth callback from Facebook — send token back to popup via postMessage."""
    if error:
        return HTMLResponse(f"""
        <script>
          window.opener && window.opener.postMessage(
            {{ type: 'META_AUTH_ERROR', error: '{error}' }},
            '{FRONTEND_ORIGIN}'
          );
          window.close();
        </script>
        <p>Erro de autenticação: {error}. Esta janela será fechada.</p>
        """)
    
    # Exchange code for access token
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"
    params = {
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.get(url, params=params)
        if res.status_code != 200:
            error_detail = res.json().get("error", {}).get("message", "Erro desconhecido")
            return HTMLResponse(f"""
            <script>
              window.opener && window.opener.postMessage(
                {{ type: 'META_AUTH_ERROR', error: '{error_detail}' }},
                '{FRONTEND_ORIGIN}'
              );
              window.close();
            </script>
            <p>Falha ao obter token. Esta janela será fechada.</p>
            """)
        
        token_data = res.json()
        access_token = token_data.get("access_token")
        
        # Send token back to frontend popup securely via postMessage
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>Conectando...</title></head>
        <body style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#0f0f13;color:#fff;">
          <div style="text-align:center">
            <div style="font-size:48px;margin-bottom:16px">✅</div>
            <h2 style="margin:0;font-size:18px">Autenticado com sucesso!</h2>
            <p style="color:#aaa;font-size:14px;margin-top:8px">Esta janela será fechada automaticamente...</p>
          </div>
          <script>
            if (window.opener) {{
              window.opener.postMessage(
                {{ type: 'META_AUTH_SUCCESS', token: '{access_token}' }},
                '{FRONTEND_ORIGIN}'
              );
            }}
            setTimeout(() => window.close(), 1500);
          </script>
        </body>
        </html>
        """)

@router.get("/meta/available-accounts")
async def get_meta_accounts(token: str):
    """List available ad accounts for a given token."""
    service = MetaService(token)
    async with service:
        accounts = await service.get_ad_accounts()
        return accounts

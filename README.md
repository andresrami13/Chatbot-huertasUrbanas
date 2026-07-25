# Chatbot de huertas urbanas — UPZ 84 Bosa Occidental

Prototipo de agente conversacional sobre WhatsApp para el apoyo a la
creacion y gestion de huertas urbanas, en el marco del Programa 25 del
Plan de Desarrollo Local de Bosa 2024-2028.

Trabajo de grado — Especializacion en Ingenieria de Software,
Universidad Distrital Francisco Jose de Caldas.

## Estado

Fase 5 — Configuracion de infraestructura. Actualmente el backend recibe
y valida los webhooks de WhatsApp; el motor conversacional aun no esta
implementado.

## Ejecucion local

    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env             # y completar los valores
    uvicorn app.main:app --reload

Comprobacion: http://localhost:8000/health

## Estructura

    app/
      main.py             Punto de entrada FastAPI
      config.py           Variables de entorno
      api/webhook.py      Controlador de webhook (GET verify + POST)
      core/signature.py   Validacion de firma X-Hub-Signature-256
      services/
        dispatcher.py     Despachador asincrono + idempotencia por wamid

## Despliegue

Railway, con arranque definido en el Procfile. Las credenciales se
configuran como variables del servicio; nunca se versionan.

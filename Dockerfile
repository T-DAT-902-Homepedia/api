FROM python:3.13-slim

WORKDIR /app

# Dépendances d'abord (cache de build).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Utilisateur non-root (bonne pratique Cloud Run).
RUN useradd --create-home appuser
USER appuser

# Cloud Run injecte PORT (8080) ; 8000 par défaut en local/compose.
ENV PORT=8000
EXPOSE 8000

# En conteneur local, la base est accessible via le service `postgis` du compose.
# Surcharger API_DATABASE_URL si besoin.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

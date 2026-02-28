# Image officielle Python
FROM python:3.12-slim

# Installer ffmpeg (pour audio/vidéo)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /app

# Copier les fichiers du bot
COPY bot.py .
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Créer un dossier pour les téléchargements
RUN mkdir downloads

# Commande pour lancer le bot
CMD ["python", "bot.py"]

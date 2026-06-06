#!/bin/bash
# Setup script for Otro Enfoque Inmobiliaria en VPS
# Ejecutar como root en un servidor Ubuntu 22.04+

set -e

DOMAIN="tudominio.com"
APP_DIR="/var/www/otroenfoque"
GIT_REPO="https://github.com/tu-usuario/otroenfoqueinmobiliaria.git"

echo "==> Actualizando sistema..."
apt update && apt upgrade -y

echo "==> Instalando dependencias..."
apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git

echo "==> Creando directorio de la app..."
mkdir -p $APP_DIR
cd $APP_DIR

echo "==> Clonando repositorio..."
git clone $GIT_REPO .

echo "==> Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

echo "==> Instalando dependencias Python..."
pip install -r requirements.txt

echo "==> Creando .env..."
cp .env.production .env
nano .env  # ← RELLENA AQUÍ: GROQ_API_KEY, ADMIN_PASSWORD, SITE_URL, WHATSAPP_NUMBER

echo "==> Configurando Nginx..."
cp deploy/nginx.conf /etc/nginx/sites-available/otroenfoque
sed -i "s/tudominio.com/$DOMAIN/g" /etc/nginx/sites-available/otroenfoque
ln -sf /etc/nginx/sites-available/otroenfoque /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "==> Certificado SSL con Let's Encrypt..."
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m admin@$DOMAIN

echo "==> Configurando servicio systemd..."
cp deploy/otroenfoque.service /etc/systemd/system/
sed -i "s|/var/www/otroenfoque|$APP_DIR|g" /etc/systemd/system/otroenfoque.service
systemctl daemon-reload
systemctl enable otroenfoque
systemctl start otroenfoque

echo "==> Verificando..."
systemctl status otroenfoque --no-pager
echo ""
echo "✅ Web desplegada en: https://$DOMAIN"
echo "📋 Admin: https://$DOMAIN/admin"
echo "⚠️  No olvides:"
echo "   1. Configurar los nameservers de Cloudflare en GoDaddy"
echo "   2. Poner el proxy de Cloudflare en modo naranja"
echo "   3. Subir las fotos de propiedades a static/properties/"

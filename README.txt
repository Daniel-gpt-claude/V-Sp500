SP500 Momentum Screener (Android PWA) - Starter (FUENTE GRATIS)

Qué es:
- Una app web instalable en Android (PWA) que muestra un screener del S&P 500.
- Un proceso automático diario (GitHub Actions) que actualiza un JSON con métricas de momentum.

Limitaciones (importante):
- La fuente GRATIS usa Yahoo Finance vía yfinance. Es buena para prueba, pero puede fallar o cambiar.
- “Precio objetivo/analistas” no está garantizado gratis. Este MVP se enfoca en momentum técnico.

Qué incluye:
1) frontend/  -> la app (estática) instalable en Android (PWA)
2) data/update_sp500.py -> genera frontend/data/sp500_momentum.json
3) .github/workflows/daily_update.yml -> corre diario y commitea el JSON

Cómo usar:
A) Crea un repo en GitHub y sube estos archivos.
B) Activa GitHub Pages (Settings -> Pages) para servir /frontend.
C) El workflow deja el JSON en /frontend/data/ para que Pages lo sirva.
D) Abre la URL en Android y elige “Agregar a pantalla de inicio”.

Privacidad:
- GitHub Pages es público. Para que sea “solo para ti”, ponle Cloudflare Access (puede ser gratis para uso personal)
  o usa un dominio/subdominio y protege el sitio con login.

Horario:
- El workflow corre L-V 13:10 UTC (~07:10 CDMX, puede variar por horario de verano).

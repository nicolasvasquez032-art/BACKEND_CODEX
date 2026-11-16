#!/usr/bin/env bash
# ==============================================================================
# TalentMatch - Script Automatizado de Pruebas de Estrés con Apache JMeter
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"

# Verificar que Java esté disponible
if ! command -v java &>/dev/null; then
  if [ -f "$HOME/.local/android-studio/jbr/bin/java" ]; then
    export PATH="$HOME/.local/android-studio/jbr/bin:$PATH"
  else
    echo "❌ Error: Java no encontrado en el sistema."
    exit 1
  fi
fi

# Verificar que JMeter esté disponible
if ! command -v jmeter &>/dev/null; then
  echo "❌ Error: JMeter no está en PATH."
  exit 1
fi

PLAN="$DIR/talentmatch_stress_test.jmx"
RESULTS="$DIR/results.jtl"
REPORT_DIR="$DIR/report_html"

THREADS=50
RAMPUP=10
DURATION=30
HOST="talentmatch-api.duckdns.org"
PORT="443"
PROTOCOL="https"
OPEN_GUI=false

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --threads|-t) THREADS="$2"; shift ;;
    --rampup|-r) RAMPUP="$2"; shift ;;
    --duration|-d) DURATION="$2"; shift ;;
    --host) HOST="$2"; shift ;;
    --port) PORT="$2"; shift ;;
    --protocol) PROTOCOL="$2"; shift ;;
    --gui|-g) OPEN_GUI=true ;;
    *) echo "Opción desconocida: $1"; exit 1 ;;
  esac
  shift
done

if [ "$OPEN_GUI" = true ]; then
  echo "🚀 Abriendo interfaz gráfica de Apache JMeter con el plan de pruebas..."
  jmeter -t "$PLAN" &
  exit 0
fi

echo "======================================================================"
echo "🎯 INICIANDO PRUEBA DE ESTRÉS TALENTMATCH CON APACHE JMETER"
echo "======================================================================"
echo "📍 Objetivo:       $PROTOCOL://$HOST:$PORT"
echo "👥 Hilos (Usuarios): $THREADS"
echo "⏱️ Ramp-up:        ${RAMPUP}s"
echo "⏳ Duración:       ${DURATION}s"
echo "📄 Plan:           $PLAN"
echo "======================================================================"

# Limpiar resultados anteriores
rm -f "$RESULTS"
rm -rf "$REPORT_DIR"

# Ejecutar JMeter en modo no-GUI (CLI) y generar reporte HTML
jmeter -n \
  -t "$PLAN" \
  -Jhost="$HOST" \
  -Jport="$PORT" \
  -Jprotocol="$PROTOCOL" \
  -Jthreads="$THREADS" \
  -Jrampup="$RAMPUP" \
  -Jduration="$DURATION" \
  -l "$RESULTS" \
  -e -o "$REPORT_DIR"

echo ""
echo "======================================================================"
echo "✅ PRUEBA COMPLETADA CON ÉXITO"
echo "======================================================================"
echo "📊 Reporte HTML Interactivo generado en:"
echo "   $REPORT_DIR/index.html"
echo ""
echo "💡 Puedes abrirlo en tu navegador con:"
echo "   xdg-open $REPORT_DIR/index.html"
echo "======================================================================"

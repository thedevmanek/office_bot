#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:1}"
export VNC_GEOMETRY="${VNC_GEOMETRY:-1600x900}"
export VNC_DEPTH="${VNC_DEPTH:-24}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export MESA_GL_VERSION_OVERRIDE="${MESA_GL_VERSION_OVERRIDE:-3.3}"
export QT_X11_NO_MITSHM="${QT_X11_NO_MITSHM:-1}"

rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

cat <<'EOF'
OpenHRI Office container is starting.

noVNC: http://localhost:6080/vnc.html?autoconnect=1&resize=remote
Object UI, after starting detector node: http://localhost:8080/

Inside the desktop, use the launchers:
- OpenHRI-Office
- OpenHRI-Object-UI
EOF

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/openhri.conf

// Script de carga HTTP para el experimento de disponibilidad.
// Ver ../docs/experimento-disponibilidad.md.
//
// Le pega al balanceador (Nginx), no a una replica directa, porque lo que
// se quiere probar es el reparto de trafico + la reaccion ante una caida.
//
// Variables de entorno:
//   BASE_URL        Default: http://localhost:18000 (Nginx del experimento)
//   ENDPOINT        Default: /ready (revisa BD + Pulsar; ver interfaces/health.py)
//   TARGET_RPS      Solicitudes por segundo a sostener. Default: 5
//   RAMP_DURATION   Tiempo para subir de 0 a TARGET_RPS. Default: 30s
//   HOLD_DURATION   Tiempo sosteniendo TARGET_RPS. Default: 5m
//
// Uso (ejemplo: fase "linea base 1x" del diseno, ilustrativa):
//   BASE_URL=http://localhost:18000 TARGET_RPS=5 HOLD_DURATION=5m k6 run carga.js
//
// Para la fase "4x", corre de nuevo con TARGET_RPS mas alto (ver seccion 3
// del diseno para como calcular ese numero para tu caso).

import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:18000';
const ENDPOINT = __ENV.ENDPOINT || '/ready';
const TARGET_RPS = Number(__ENV.TARGET_RPS || 5);
const RAMP_DURATION = __ENV.RAMP_DURATION || '30s';
const HOLD_DURATION = __ENV.HOLD_DURATION || '5m';

export const options = {
  scenarios: {
    carga_notificaciones: {
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: Math.max(20, TARGET_RPS * 2),
      maxVUs: Math.max(50, TARGET_RPS * 5),
      stages: [
        { target: TARGET_RPS, duration: RAMP_DURATION },
        { target: TARGET_RPS, duration: HOLD_DURATION },
      ],
    },
  },
};

export default function () {
  const res = http.get(`${BASE_URL}${ENDPOINT}`);
  check(res, {
    'codigo 2xx': (r) => r.status >= 200 && r.status < 300,
    'trae X-Instance-Id': (r) => r.headers['X-Instance-Id'] !== undefined,
  });
}

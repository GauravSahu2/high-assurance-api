import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    stress_test: {
      executor: 'ramping-arrival-rate',
      preAllocatedVUs: 50,
      timeUnit: '1s',
      stages: [
        { duration: '2m', target: 100 }, // Ramp up to 100 req/s
        { duration: '5m', target: 100 }, // Sustain stress load
        { duration: '2m', target: 0 },   // Graceful scale down
      ],
    },
  },
  thresholds: {
    // The Mathematical Enforcement:
    'http_req_duration': ['p95<200', 'p99<500'], // 99% of requests MUST complete under 500ms
    'http_req_failed': ['rate<0.001'],           // Error rate MUST be strictly less than 0.1%
  },
};

export default function () {
  const res = http.get('http://localhost:8000/api/health');
  check(res, {
    'is status 200': (r) => r.status === 200,
  });
}

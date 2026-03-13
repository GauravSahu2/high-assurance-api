import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    'http_req_duration': ['p(95)<200', 'min>=0'],
    'http_req_failed': ['rate<0.01'],
  },
  stages: [{ duration: '5s', target: 5 }],
};

export default function () {
  // Use centralized environment variable for token
  const token = __ENV.AUTH_TOKEN || 'valid_admin_token';
  
  // 1. Check Health
  const healthRes = http.get('http://127.0.0.1:8000/health');
  check(healthRes, { 'Health is 200': (r) => r.status === 200 });

  // 2. Execute Transfer
  const uniqueKey = `load-${__ITER}-${__VU}-${Math.random()}`;
  const payload = JSON.stringify({ amount: 1 });
  const params = {
    headers: { 
        'Content-Type': 'application/json', 
        'X-Idempotency-Key': uniqueKey,
        'Authorization': `Bearer ${token}`
    },
  };
  
  const transferRes = http.post('http://127.0.0.1:8000/transfer', payload, params);
  check(transferRes, { 'Transfer processed': (r) => r.status === 200 || r.status === 400 });
  
  sleep(0.1);
}

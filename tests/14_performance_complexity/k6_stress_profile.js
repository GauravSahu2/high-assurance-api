import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    // Using p(95) and p(99) is the most compatible syntax for all k6 versions
    'http_req_duration': ['p(95)<200', 'p(99)<500'], 
    'http_req_failed': ['rate<0.01'],
  },
  stages: [
    { duration: '5s', target: 20 }, // Ramp up
    { duration: '10s', target: 20 }, // Stay at peak
    { duration: '5s', target: 0 },  // Ramp down
  ],
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/health');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'protocol is HTTP/1.1': (r) => r.proto === 'HTTP/1.1',
  });
  sleep(1);
}

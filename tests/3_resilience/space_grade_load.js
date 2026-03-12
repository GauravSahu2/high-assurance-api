import http from 'k6/http';
import { sleep, check } from 'k6';

// Space-Grade Configuration
export const options = {
  stages: [
    { duration: '5s', target: 50 },   // Stage 1: Load (Ramp up to normal traffic)
    { duration: '10s', target: 50 },  // Stage 2: Hold normal traffic
    { duration: '5s', target: 500 },  // Stage 3: STRESS SPIKE (10x traffic in 5 seconds)
    { duration: '10s', target: 500 }, // Stage 4: Hold the spike
    { duration: '5s', target: 0 },    // Stage 5: Ramp down safely
  ],
  thresholds: {
    // Strict FDA/Fintech Rules:
    http_req_duration: ['p(95)<500'], // 95% of requests MUST complete below 500ms
    http_req_failed: ['rate<0.01'],   // Error rate MUST be strictly less than 1%
  },
};

export default function () {
  // Mocking a heavy API calculation (calculating Pi) to test server CPU stress
  const res = http.get('https://test.k6.io/pi.php?decimals=3');
  
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  
  sleep(1); // Simulate realistic user wait time between clicks
}

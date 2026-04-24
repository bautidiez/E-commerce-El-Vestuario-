import { isDevMode } from '@angular/core';

export const environment = {
  production: !isDevMode(),
  apiUrl: !isDevMode()
    ? 'https://elvestuario-backend.onrender.com/api'
    : 'http://localhost:5000/api',
  firebase: {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_AUTH_DOMAIN",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_STORAGE_BUCKET",
    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
    appId: "YOUR_APP_ID"
  }
};

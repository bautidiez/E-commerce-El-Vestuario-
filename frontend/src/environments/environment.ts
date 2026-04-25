import { isDevMode } from '@angular/core';

export const environment = {
  production: !isDevMode(),
  apiUrl: !isDevMode()
    ? 'https://elvestuario-backend.onrender.com/api'
    : 'http://localhost:5000/api',
  firebase: {
    apiKey: "AIzaSyDmsMC3cldmpoB30XCI_0d_wvnpYnA1X6w",
    authDomain: "el-vestuario.firebaseapp.com",
    projectId: "el-vestuario",
    storageBucket: "el-vestuario.firebasestorage.app",
    messagingSenderId: "875667453769",
    appId: "1:875667453769:web:702e0b8c13d8ee5b920c98",
    measurementId: "G-88L0PPFT2H"
  }
};

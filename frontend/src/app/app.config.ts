// Deployment Version: 1.1.2 - Admin UI Improvements
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { LOCALE_ID } from '@angular/core';
import { registerLocaleData } from '@angular/common';
import localeEsAr from '@angular/common/locales/es-AR';

registerLocaleData(localeEsAr);

import { provideFirebaseApp, initializeApp } from '@angular/fire/app';
import { provideAuth, getAuth } from '@angular/fire/auth';
import { environment } from '../environments/environment';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptorsFromDi()),
    provideFirebaseApp(() => initializeApp(environment.firebase)),
    provideAuth(() => getAuth()),
    {
      provide: 'RECAPTCHA_SETTINGS',
      useValue: {
        siteKey: '6LfgSlssAAAAALlGb4Fnu9-AoIkKNGOCAGydHwOB', // CLAVE DE PRODUCCION
      },
    },
    { provide: LOCALE_ID, useValue: 'es-AR' }
  ]
};

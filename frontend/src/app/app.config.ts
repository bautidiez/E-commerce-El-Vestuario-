import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { LOCALE_ID } from '@angular/core';
import { registerLocaleData } from '@angular/common';
import localeEsAr from '@angular/common/locales/es-AR';

registerLocaleData(localeEsAr);

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptorsFromDi()),
    {
      provide: 'RECAPTCHA_SETTINGS',
      useValue: {
        siteKey: '6LfgSlssAAAAALlGb4Fnu9-AoIkKNGOCAGydHwOB', // CLAVE DE PRODUCCION
      },
    },
    { provide: LOCALE_ID, useValue: 'es-AR' }
  ]
};

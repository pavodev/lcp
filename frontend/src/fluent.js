import { FluentBundle, FluentResource } from '@fluent/bundle';
import { createFluentVue } from 'fluent-vue';
import enMessages from './locales/en.ftl';
import itMessages from './locales/it.ftl';

// Create bundles for locales that will be used
const enBundle = new FluentBundle('en');
enBundle.addResource(new FluentResource(enMessages));
const itBundle = new FluentBundle('it');
itBundle.addResource(new FluentResource(itMessages));

// Create plugin istance
// bundles - The current negotiated fallback chain of languages
export const fluent = createFluentVue({
  bundles: [enBundle, itBundle]
});

export function changeLocale (locale) {
  if(locale === 'en'){
    fluent.bundles = [enBundle];
  } else if (locale === 'it'){
    fluent.bundles = [itBundle];
  } else {
    fluent.bundles = [enBundle];
  }
}
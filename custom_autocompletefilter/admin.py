import django
from django.contrib.admin.widgets import SELECT2_TRANSLATIONS
from django.utils.datastructures import OrderedSet
from django.utils.translation import get_language


class AutocompleteFilterMixin:

    @property
    def media(self):
        media = super().media

        i18n_file = None
        i18n_name = SELECT2_TRANSLATIONS.get(get_language(), None)
        if i18n_name:
            i18n_file = 'admin/js/vendor/select2/i18n/%s.js' % i18n_name

        extra_js = [
            'admin/js/vendor/jquery/jquery.js',
            'admin/js/vendor/select2/select2.full.js',
        ]
        if i18n_file:
            extra_js.append(i18n_file)
        extra_js.extend([
            'admin/js/jquery.init.js',
            'admin/js/autocomplete.js',
            'js/autocomplete_filter.js',
        ])
        extra_css = [
            'admin/css/vendor/select2/select2.css',
            'admin/css/autocomplete.css',
        ]
        if django.VERSION >= (2, 2, 0, 'final', 0):
            media._js_lists.append(extra_js)
            media._css_lists.append({'screen': extra_css})
        else:
            media._js = OrderedSet(extra_js + media._js)
            media._css.setdefault('screen', [])
            media._css['screen'].extend(extra_css)
        return media

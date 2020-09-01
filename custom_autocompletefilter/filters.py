from django.contrib.admin.filters import (AllValuesFieldListFilter,
                                          RelatedFieldListFilter)
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.utils import reverse_field_path
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import NoReverseMatch, reverse


def get_request():
    """Walk the stack up to find a request in a context variable."""
    import inspect
    frame = None
    try:
        for f in inspect.stack()[1:]:
            frame = f[0]
            code = frame.f_code
            if code.co_varnames and 'context' in code.co_varnames:
                return frame.f_locals['context']['request']
    finally:
        del frame


class MultipleAutocompleteListFilter(RelatedFieldListFilter):
    template = 'admin/multiple_filter_autocomplete.html'

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = '%s__%s__in' % (field_path, field.target_field.name)
        self.lookup_kwarg_isnull = '%s__isnull' % field_path
        lookup_vals = request.GET.get(self.lookup_kwarg)
        self.lookup_val = lookup_vals.split(',') if lookup_vals else list()
        super(RelatedFieldListFilter, self).__init__(field, request, params, model, model_admin, field_path)

    def has_output(self):
        """Show the autocomplete filter at all times."""
        return True

    @staticmethod
    def get_admin_namespace():
        request = get_request()
        return request.resolver_match.namespace

    def get_url(self):
        model = self.field.related_model
        args = (
            model._meta.app_label,
            model._meta.model_name,
        )
        try:
            return reverse('admin:%s_%s_autocomplete' % args)
        except NoReverseMatch:
            # Admin is registered under a different namespace!
            args = (
                self.get_admin_namespace(),
                *args,
            )
            return reverse('%s:%s_%s_autocomplete' % args)

    def field_choices(self, field, request, model_admin):
        # Do not populate the field choices with a huge queryset
        return []

    def choices(self, changelist):
        """
        Get choices for the widget.
        """
        url = self.get_url()

        placeholder = 'PKVAL'
        query_string = changelist.get_query_string({
            self.lookup_kwarg: placeholder,
        }, [self.lookup_kwarg_isnull])

        if self.lookup_val.__len__() == 0:
            yield {
                'url': url,
                'selected': None,
                'selected_display': None,
                'query_string': query_string,
                'query_string_placeholder': placeholder,
                'query_string_all': changelist.get_query_string(
                    {}, [self.lookup_kwarg, self.lookup_kwarg_isnull]
                ),
            }

        for val in self.lookup_val:
            instance = self.field.related_model.objects.get(pk=val)
            lookup_display = str(instance)

            yield {
                'url': url,
                'selected': val,
                'selected_display': lookup_display,
                'query_string': query_string,
                'query_string_placeholder': placeholder,
                'query_string_all': changelist.get_query_string(
                    {}, [self.lookup_kwarg, self.lookup_kwarg_isnull]
                ),
            }


class MultiSelectMixin(object):
    def queryset(self, request, queryset):
        params = Q()
        for lookup_arg, value in self.used_parameters.items():
            params |= Q(**{lookup_arg: value})
        try:
            return queryset.filter(params)
        except (ValueError, ValidationError) as e:
            # Fields may raise a ValueError or ValidationError when converting
            # the parameters to the correct type.
            raise IncorrectLookupParameters(e)

    def querystring_for_choices(self, val, changelist):
        lookup_vals = self.lookup_vals[:]
        if val in self.lookup_vals:
            lookup_vals.remove(val)
        else:
            lookup_vals.append(val)
        if lookup_vals:
            query_string = changelist.get_query_string({
                self.lookup_kwarg: ','.join(lookup_vals),
            }, [])
        else:
            query_string = changelist.get_query_string(
                {}, [self.lookup_kwarg]
            )
        return query_string

    def querystring_for_isnull(self, changelist):
        if self.lookup_val_isnull:
            query_string = changelist.get_query_string(
                {}, [self.lookup_kwarg_isnull]
            )
        else:
            query_string = changelist.get_query_string({
                self.lookup_kwarg_isnull: 'True',
            }, [])
        return query_string


class AutocompleteListFilter(MultiSelectMixin, AllValuesFieldListFilter):
    template = 'admin/multiple_filter_autocomplete.html'

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = '%s__in' % field_path
        self.lookup_kwarg_isnull = '%s__isnull' % field_path
        lookup_vals = request.GET.get(self.lookup_kwarg)
        self.lookup_vals = lookup_vals.split(',') if lookup_vals else list()
        self.lookup_val_isnull = request.GET.get(self.lookup_kwarg_isnull)
        self.empty_value_display = model_admin.get_empty_value_display()
        self.parent_model, self.reverse_path = reverse_field_path(model, field_path)
        super(AllValuesFieldListFilter, self).__init__(field, request, params, model, model_admin, field_path)

    def prepare_querystring_value(self, value):
        # mask all commas or these values will be used
        # in a comma-seperated-list as get-parameter
        return str(value).replace(',', '%~')

    def choices(self, changelist):
        placeholder = 'PKVAL'
        query_string = changelist.get_query_string({
            self.lookup_kwarg: placeholder,
        }, [self.lookup_kwarg_isnull])

        if self.lookup_vals.__len__() == 0:
            yield {
                'url': reverse('gift:field_autocomplete'),
                'selected': None,
                'selected_display': None,
                'query_string': query_string,
                'query_string_placeholder': placeholder,
                'query_string_all': changelist.get_query_string(
                    {}, [self.lookup_kwarg, self.lookup_kwarg_isnull]
                ),
            }
        else:
            for val in self.lookup_vals:
                yield {
                    'url': reverse('gift:field_autocomplete'),
                    'selected': val,
                    'selected_display': val,
                    'query_string': query_string,
                    'query_string_placeholder': placeholder,
                    'query_string_all': changelist.get_query_string(
                        {}, [self.lookup_kwarg, self.lookup_kwarg_isnull]
                    ),
                }

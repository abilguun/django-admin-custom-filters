class Select2ViewMixin(object):
    """View mixin to render a JSON response for Select2."""

    def get_results(self, context):
        """Return data for the 'results' key of the response."""
        return [
            {
                'id': self.get_result_value(result),
                'text': self.get_result_value(result),
                'selected_text': self.get_result_value(result),
            } for result in context['object_list']
        ]

    def get_create_option(self, context, q):
        """Form the correct create_option to append to results."""
        create_option = []
        display_create_option = False
        if self.create_field and q:
            page_obj = context.get('page_obj', None)
            if page_obj is None or page_obj.number == 1:
                display_create_option = True

            # Don't offer to create a new option if a
            # case-insensitive) identical one already exists
            existing_options = (self.get_result_label(result).lower()
                                for result in context['object_list'])
            if q.lower() in existing_options:
                display_create_option = False

        if display_create_option and self.has_add_permission(self.request):
            create_option = [{
                'id': q,
                'text': _('Create "%(new_value)s"') % {'new_value': q},
                'create_id': True,
            }]
        return create_option

    def render_to_response(self, context):
        """Return a JSON response in Select2 format."""
        q = self.request.GET.get('q', None)

        create_option = self.get_create_option(context, q)

        return JsonResponse(
            {
                'results': self.get_results(context) + create_option,
                'pagination': {
                    'more': self.has_more(context)
                }
            })


class ViewMixin(object):
    """Common methods for autocomplete views.
    It is assumed this view will be used in conjunction with a Django
    :py:class:`View` based class that will that will implement OPTIONS.
    .. py:attribute:: forwarded
        Dict of field values that were forwarded from the form, may be used to
        filter autocompletion results based on the form state. See
        ``linked_data`` example for reference.
    .. py:attribute:: q
        Query string as typed by the user in the autocomplete field.
    """

    http_method_allowed = ('GET', 'POST')

    def dispatch(self, request, *args, **kwargs):
        """Set :py:attr:`forwarded` and :py:attr:`q`."""
        if request.method.upper() not in self.http_method_allowed:
            return HttpResponseNotAllowed(self.http_method_allowed)

        try:
            self.forwarded = json.loads(
                getattr(request, request.method).get('forward', '{}')
            )
        except ValueError:
            return HttpResponseBadRequest('Invalid JSON data')

        if not isinstance(self.forwarded, dict):
            return HttpResponseBadRequest('Not a JSON object')

        self.q = request.GET.get('q', '')
        return super(ViewMixin, self).dispatch(request, *args, **kwargs)


class BaseQuerySetView(ViewMixin, BaseListView):
    """Base view to get results from a QuerySet.
    .. py:attribute:: create_field
        Name of the field to use to create missing values. For example, if
        create_field='title', and the user types in "foo", then the
        autocomplete view will propose an option 'Create "foo"' if it can't
        find any value matching "foo". When the user does click 'Create "foo"',
        the autocomplete script should POST to this view to create the object
        and get back the newly created object id.
    .. py:attribute:: model_field_name
        Name of the Model field to run filter against.
    """

    paginate_by = 10
    context_object_name = 'results'
    model_field_name = 'city'
    create_field = 'city'

    def has_more(self, context):
        """For widgets that have infinite-scroll feature."""
        return context['page_obj'].has_next() if context['page_obj'] else False

    def get_result_value(self, result):
        """Return the value of a result."""
        return str(result['city'])

    def get_result_label(self, result):
        """Return the label of a result."""
        return six.text_type(result)

    def get_selected_result_label(self, result):
        """Return the label of a selected result."""
        return self.get_result_label(result)

    def get_queryset(self):
        """Filter the queryset with GET['q']."""
        qs = super(BaseQuerySetView, self).get_queryset()

        if self.q:
            qs = qs.filter(**{'%s__icontains' % self.model_field_name: self.q})

        return qs

    def create_object(self, text):
        """Create an object given a text."""
        return self.get_queryset().get_or_create(
            **{self.create_field: text})[0]

    def has_add_permission(self, request):
        """Return True if the user has the permission to add a model."""
        if django.VERSION < (2, 0, 0):
            auth = request.user.is_authenticated()
        else:
            auth = request.user.is_authenticated

        if not auth:
            return False

        opts = self.get_queryset().model._meta
        codename = get_permission_codename('add', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def post(self, request, *args, **kwargs):
        """Create an object given a text after checking permissions."""
        if not self.has_add_permission(request):
            return HttpResponseForbidden()

        if not self.create_field:
            raise ImproperlyConfigured('Missing "create_field"')

        text = request.POST.get('text', None)

        if text is None:
            return HttpResponseBadRequest()

        result = self.create_object(text)

        return JsonResponse({
            'id': result.pk,
            'text': self.get_result_label(result),
        })


class Select2QuerySetView(Select2ViewMixin, BaseQuerySetView):
    """List options for a Select2 widget."""


class FieldAutoComplete(Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Item.objects.none()


        # get data from DB or cache
        # キャッシュからデータを取る
        cities = cache.get('cities')
        if cities is None:
            return []

        arg = self.request.GET.get('term')
        if arg:
            autocomplete_result = []
            for city_ in (city for city in cities if arg in city["city"]):
                autocomplete_result.append(city_)
            return autocomplete_result

        return cities

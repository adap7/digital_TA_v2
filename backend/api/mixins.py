class TenantScopedQuerysetMixin:
    """
    Ensures all querysets are filtered by the authenticated user's tenant.
    """

    tenant_field = "tenant"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none()

        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return queryset.none()

        return queryset.filter(**{self.tenant_field: tenant})

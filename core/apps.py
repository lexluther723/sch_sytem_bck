from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Shared, cross-app infrastructure.

    Nothing in this app is school-domain-specific — it only holds
    reusable plumbing (pagination, caching helpers, mixins, base
    filters) that every other app imports instead of re-inventing.
    Centralising this here is what lets us change "how every list
    endpoint paginates" or "how every endpoint caches" in ONE place.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core (shared infrastructure)"

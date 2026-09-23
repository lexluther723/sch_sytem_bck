"""
Caching helpers for expensive, rarely-changing, read-heavy endpoints.

WHERE THIS MATTERS MOST
------------------------
`dashboard/` and `reports/` run multiple `.aggregate()` /
`.annotate()` queries (sums across fee payments, attendance %,
exam averages, class rankings...) on every single page load, even
though the underlying numbers only change when someone submits a
payment, marks attendance, or enters results — i.e. rarely relative
to how often a dashboard is *viewed* (every page refresh, every time
a parent/teacher opens the app).

Instead of re-running the same aggregate queries for every request,
we cache the computed result for a short TTL (30–120s depending on
volatility) and invalidate proactively the moment underlying data
changes (via `bust_cache_prefix`, called from the relevant
save()/signal — see fees/signals.py and results/services.py for
where this is wired in).

This is a *cache-aside* pattern using Django's cache framework
(`django.core.cache.cache`), configured in settings.py. In dev this
is LocMemCache; in production point `CACHES["default"]` at Redis/
Memcached so the cache is shared across worker processes instead of
being duplicated (and instantly invalid) per-process.
"""

import hashlib

from django.core.cache import cache


def make_cache_key(prefix: str, *parts) -> str:
    """
    Build a deterministic, collision-resistant cache key from a
    prefix plus any number of identifying parts (user id, role,
    term, academic year, query params, ...).

    Using a prefix namespace (e.g. "dashboard:teacher") lets us bust
    every key under that namespace together via `bust_cache_prefix`,
    without needing to know every exact key that was ever generated.
    """
    raw = ":".join(str(p) for p in parts)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def get_or_set_cached(prefix: str, parts, builder, timeout: int = 60):
    """
    Cache-aside helper: return the cached value for (prefix, parts)
    if present, otherwise call `builder()` to compute it, store it,
    and return it.

    `builder` is only called on a cache miss — this is the whole
    point: expensive aggregation only runs when the cache is cold or
    expired, not on every request.
    """
    key = make_cache_key(prefix, *parts)
    value = cache.get(key)
    if value is None:
        value = builder()
        cache.set(key, value, timeout)
    return value


def _index_key(prefix: str) -> str:
    """
    Cache key holding the set of keys registered under `prefix`.

    BUG THIS FIXES
    --------------
    `get_or_set_cached_indexed` registered keys under the FULL prefix
    it was called with (e.g. "dashboard:summary"), producing an index
    at "dashboard:summary:__keys__". But `bust_cache_prefix` was being
    called with the PARENT namespace ("dashboard"), so it looked up
    "dashboard:__keys__" - a key nothing ever wrote. Invalidation
    therefore deleted nothing, and dashboards served stale numbers for
    the full TTL after every payment.

    Fix: keys are registered against every ancestor namespace, so
    busting "dashboard" clears "dashboard:summary",
    "dashboard:top_outstanding_students", and anything else added
    later, without the caller needing to know the exact sub-prefix.
    """
    return f"{prefix}:__keys__"


def _namespaces(prefix: str):
    """"a:b:c" -> ["a", "a:b", "a:b:c"]"""
    parts = prefix.split(":")
    return [":".join(parts[: i + 1]) for i in range(len(parts))]


def bust_cache_prefix(prefix: str):
    """
    Invalidate every cache entry registered under `prefix`.

    Django's low-level cache API has no native "delete by prefix"
    (that's a Redis/Memcached-server-side concept), so we keep a
    lightweight index of keys per prefix (a set, stored in the same
    cache backend) and delete them explicitly. This keeps the
    dependency-free LocMemCache backend working the same way Redis
    would in production.

    Call this from wherever the underlying data changes, e.g.:
        - fees/signals.py after a FeePayment is saved
        - results/services.py after results are finalized
        - attendance/views.py after attendance is submitted
    """
    index_key = _index_key(prefix)
    keys = cache.get(index_key, set())
    if keys:
        cache.delete_many(list(keys))
    cache.delete(index_key)


def get_or_set_cached_indexed(prefix: str, parts, builder, timeout: int = 60):
    """
    Same as `get_or_set_cached`, but also registers the generated key
    in the prefix's index so `bust_cache_prefix(prefix)` can find and
    clear it later. Use this version for anything you'll need to
    invalidate on writes (which is almost everything dashboard-related).
    """
    key = make_cache_key(prefix, *parts)
    value = cache.get(key)
    if value is None:
        value = builder()
        cache.set(key, value, timeout)
        # Register the key under EVERY ancestor namespace so a coarse
        # bust_cache_prefix("dashboard") reaches keys stored under
        # "dashboard:summary", "dashboard:top_students", etc.
        for namespace in _namespaces(prefix):
            index_key = _index_key(namespace)
            keys = cache.get(index_key, set())
            keys.add(key)
            cache.set(index_key, keys, timeout * 10)
    return value

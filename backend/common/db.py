from contextlib import contextmanager
from django.db import transaction


@contextmanager
def atomic():
    with transaction.atomic():
        yield



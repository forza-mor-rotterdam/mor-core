from contextvars import ContextVar

from django.conf import settings

active_db = ContextVar(settings.DEFAULT_DATABASE_KEY, default=None)


def get_active_db():
    db = active_db.get(None)
    return db if db else settings.DEFAULT_DATABASE_KEY


def set_active_db(connection_name):
    return active_db.set(connection_name)


class DatabaseRouter:
    @staticmethod
    def _get_db(*args, **kwargs):
        db = (
            get_active_db()
            if settings.ENVIRONMENT not in ["unittest"]
            else settings.DEFAULT_DATABASE_KEY
        )
        return db

    db_for_read = _get_db
    db_for_write = _get_db

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == settings.DEFAULT_DATABASE_KEY

"""
Management utility to create superusers.
"""
import os
import re
import sys

from django.contrib.auth import get_user_model
from django.core import exceptions
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import DEFAULT_DB_ALIAS
from django.utils.functional import cached_property
from django.utils.text import capfirst


class NotRunningInTTYException(Exception):
    pass


PASSWORD_FIELD = "password"


class Command(BaseCommand):
    help = "Used to create a superuser."
    requires_migrations_checks = True
    stealth_options = ("stdin",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.UserModel = get_user_model()
        self.username_field = self.UserModel._meta.get_field(
            self.UserModel.USERNAME_FIELD
        )

    def add_arguments(self, parser):
        parser.add_argument(
            "--%s" % self.UserModel.USERNAME_FIELD,
            help="Specifies the login for the superuser.",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help=(
                "Tells Django to NOT prompt the user for input of any kind. "
                "You must use --%s with --noinput, along with an option for "
                "any other required field. Superusers created with --noinput will "
                "not be able to log in until they're given a valid password."
                % self.UserModel.USERNAME_FIELD
            ),
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use. Default is "default".',
        )
        for field_name in self.UserModel.REQUIRED_FIELDS:
            field = self.UserModel._meta.get_field(field_name)
            if field.many_to_many:
                if (
                    field.remote_field.through
                    and not field.remote_field.through._meta.auto_created
                ):
                    raise CommandError(
                        "Required field '%s' specifies a many-to-many "
                        "relation through model, which is not supported." % field_name
                    )
                else:
                    parser.add_argument(
                        "--%s" % field_name,
                        action="append",
                        help=(
                            "Specifies the %s for the superuser. Can be used "
                            "multiple times." % field_name,
                        ),
                    )
            else:
                parser.add_argument(
                    "--%s" % field_name,
                    help="Specifies the %s for the superuser." % field_name,
                )

    def execute(self, *args, **options):
        self.stdin = options.get("stdin", sys.stdin)  # Used for testing
        return super().execute(*args, **options)

    def password_exists_for_username_var(self, env_var):
        return os.environ.get(f"{env_var.replace('_USERNAME', '_PASSWORD')}", "____")

    def handle(self, *args, **options):
        username = options[self.UserModel.USERNAME_FIELD]
        database = options["database"]
        user_data = {}
        verbose_field_name = self.username_field.verbose_name
        pattern = re.compile(r"DJANGO_USER_\w+_USERNAME")
        users = []
        for key, val in os.environ.items():
            if pattern.match(key):
                email = os.environ.get(key)
                try:
                    validate_email(email)
                except ValidationError:
                    email = f"{os.environ.get(key)}@forzamor.nl"
                if self.password_exists_for_username_var(key):
                    users.append(
                        (
                            email,
                            self.password_exists_for_username_var(key),
                        )
                    )

        try:
            self.UserModel._meta.get_field(PASSWORD_FIELD)
        except exceptions.FieldDoesNotExist:
            pass
        else:
            # If not provided, create the user with an unusable password.
            user_data[PASSWORD_FIELD] = None
        try:
            # Non-interactive mode.
            # Use password from environment variable, if provided.
            for user in users:
                username = user[0]
                error_msg = self._validate_username(
                    username, verbose_field_name, database
                )
                if error_msg:
                    continue
                user_data[PASSWORD_FIELD] = user[1]
                user_data[self.UserModel.USERNAME_FIELD] = username
                self.UserModel._default_manager.db_manager(database).create_user(
                    **user_data
                )
            if options["verbosity"] >= 1:
                self.stdout.write("Users created successfully.")

        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled.")
            sys.exit(1)
        except exceptions.ValidationError as e:
            raise CommandError("; ".join(e.messages))
        except NotRunningInTTYException:
            self.stdout.write(
                "Superuser creation skipped due to not running in a TTY. "
                "You can run `manage.py createsuperuser` in your project "
                "to create one manually."
            )

    def get_input_data(self, field, message, default=None):
        """
        Override this method if you want to customize data inputs or
        validation exceptions.
        """
        raw_value = input(message)
        if default and raw_value == "":
            raw_value = default
        try:
            val = field.clean(raw_value, None)
        except exceptions.ValidationError as e:
            self.stderr.write("Error: %s" % "; ".join(e.messages))
            val = None

        return val

    def _get_input_message(self, field, default=None):
        m2m_target_field_name = (
            field.m2m_target_field_name()
            if field.many_to_many
            else field.remote_field.field_name
        )
        return "%s%s%s: " % (
            capfirst(field.verbose_name),
            " (leave blank to use '%s')" % default if default else "",
            " (%s.%s)"
            % (
                field.remote_field.model._meta.object_name,
                m2m_target_field_name,
            )
            if field.remote_field
            else "",
        )

    @cached_property
    def username_is_unique(self):
        if self.username_field.unique:
            return True
        return any(
            len(unique_constraint.fields) == 1
            and unique_constraint.fields[0] == self.username_field.name
            for unique_constraint in self.UserModel._meta.total_unique_constraints
        )

    def _validate_username(self, username, verbose_field_name, database):
        """Validate username. If invalid, return a string error message."""
        if self.username_is_unique:
            try:
                self.UserModel._default_manager.db_manager(database).get_by_natural_key(
                    username
                )
            except self.UserModel.DoesNotExist:
                pass
            else:
                return "Error: That %s is already taken." % verbose_field_name
        if not username:
            return "%s cannot be blank." % capfirst(verbose_field_name)
        try:
            self.username_field.clean(username, None)
        except exceptions.ValidationError as e:
            return "; ".join(e.messages)

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from accounts.repository import get_user_by_username, set_password_hash


class Command(BaseCommand):
    help = "Set a Django-compatible password hash in Oracle LMS_USER."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("password")

    def handle(self, *args, **options):
        user = get_user_by_username(options["username"])
        if not user:
            raise CommandError("LMS_USER was not found.")

        password_hash = make_password(options["password"])
        set_password_hash(int(user["user_id"]), password_hash)

        self.stdout.write(
            self.style.SUCCESS(
                f"Password updated for {user['username']}."
            )
        )

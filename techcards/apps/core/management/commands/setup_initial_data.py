"""
Management command to populate initial data:
  - NDT methods and normative documents (via ndt_data registry)
  - Default tariff plans
  - Demo changelog entry
  - Optional superuser
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from apps.payments.models import TariffPlan


class Command(BaseCommand):
    help = "Populate database with initial application data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Create a default superuser (admin/admin123)",
        )

    def handle(self, *args, **options):
        self._setup_site()
        self._setup_tariffs()
        self._setup_standards()
        self._setup_changelog()
        if options["superuser"]:
            self._create_superuser()
        self.stdout.write(self.style.SUCCESS("Initial data setup complete."))

    def _setup_site(self):
        Site.objects.update_or_create(
            id=1,
            defaults={"domain": "localhost:8000", "name": "НКТехКарты"},
        )
        self.stdout.write("  ✓ Site configured")

    def _setup_tariffs(self):
        tariff_data = settings.TARIFF_PLANS
        for i, plan in enumerate(tariff_data):
            TariffPlan.objects.update_or_create(
                cards_count=plan["cards"],
                defaults={"price": Decimal(str(plan["price"])), "sort_order": i, "is_active": True},
            )
        self.stdout.write(f"  ✓ {len(tariff_data)} tariffs created/updated")

    def _setup_standards(self):
        from ndt_data.registry import populate_standards
        populate_standards()
        self.stdout.write("  ✓ NDT methods and documents populated")

    def _setup_changelog(self):
        from django.utils import timezone
        from apps.core.models import ChangelogEntry

        ChangelogEntry.objects.get_or_create(
            title="Запуск приложения НКТехКарты",
            defaults={
                "body": (
                    "Добавлена поддержка методов НК: ВИК (РД 03-606-03, ГОСТ Р ИСО 17637), "
                    "РК (ГОСТ 7512-82, НП-105-18), ПВК (ГОСТ Р ИСО 3452-1), "
                    "КГ (ГОСТ Р 52005-2003). Реализована автоматическая разработка "
                    "технологических карт и оценка качества сварных соединений."
                ),
                "is_published": True,
                "published_at": timezone.now(),
            },
        )
        self.stdout.write("  ✓ Changelog entry created")

    def _create_superuser(self):
        from apps.accounts.models import User

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="admin123",
                role=User.Role.ADMIN,
            )
            self.stdout.write(self.style.WARNING("  ✓ Superuser 'admin' created with password 'admin123' — CHANGE IN PRODUCTION!"))
        else:
            self.stdout.write("  - Superuser 'admin' already exists")

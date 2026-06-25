"""
Команда управления для первоначальной загрузки данных.

Создаёт нормативные документы, тарифные планы и тестового суперпользователя.

Использование:
    python manage.py init_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from techcards.models import NormativeDocument
from payments.models import TariffPlan
from accounts.models import UserBalance

User = get_user_model()


class Command(BaseCommand):
    help = 'Первоначальная загрузка данных (нормативные документы, тарифы, суперпользователь)'

    def add_arguments(self, parser):
        parser.add_argument('--admin-password', type=str, default='admin',
                            help='Пароль для суперпользователя (по умолчанию: admin)')

    def handle(self, *args, **options):
        self.stdout.write('Загрузка нормативных документов...')
        self._create_normative_docs()

        self.stdout.write('Загрузка тарифных планов...')
        self._create_tariffs()

        self.stdout.write('Создание тем форума...')
        self._create_forum_rooms()

        self.stdout.write('Создание суперпользователя...')
        self._create_superuser(options['admin_password'])

        self.stdout.write(self.style.SUCCESS('Данные успешно загружены!'))

    def _create_normative_docs(self):
        """Создаёт записи нормативных документов."""
        docs = [
            {
                'code': 'ГОСТ Р 50.05.07-2018',
                'full_name': (
                    'ГОСТ Р 50.05.07-2018 «Система экспертной оценки и подтверждения '
                    'соответствия объектов использования атомной энергии. '
                    'Неразрушающий контроль. Радиографический контроль»'
                ),
                'control_method': 'RT',
                'is_implemented': True,
                'is_active': True,
                'sort_order': 10,
                'document_kind': NormativeDocument.KIND_METHODOLOGICAL,
                'description': (
                    'Определяет технические требования к радиографическому контролю '
                    'оборудования и трубопроводов атомных энергетических установок.'
                ),
            },
            {
                'code': 'ГОСТ 7512-82',
                'full_name': 'ГОСТ 7512-82 «Контроль неразрушающий. Сварные соединения. Радиографический метод»',
                'control_method': 'RT',
                'is_implemented': False,
                'is_active': True,
                'sort_order': 20,
                'description': 'Общие требования к радиографическому контролю сварных соединений.',
            },
            {
                'code': 'СТО 2-3.2-318-2018',
                'full_name': 'СТО 2-3.2-318-2018 «Технические требования к визуальному и измерительному контролю»',
                'control_method': 'VT',
                'is_implemented': False,
                'is_active': True,
                'sort_order': 30,
                'description': 'Визуальный и измерительный контроль сварных соединений.',
            },
            {
                'code': 'ГОСТ Р 50.05.09-2018',
                'full_name': 'ГОСТ Р 50.05.09-2018 «Капиллярный контроль. АЭУ»',
                'control_method': 'PT',
                'is_implemented': False,
                'is_active': True,
                'sort_order': 40,
                'description': 'Капиллярный контроль в области атомной энергетики.',
            },
            {
                'code': 'ГОСТ Р 50.05.10-2018',
                'full_name': 'ГОСТ Р 50.05.10-2018 «Контроль герметичности. АЭУ»',
                'control_method': 'LT',
                'is_implemented': False,
                'is_active': True,
                'sort_order': 50,
                'description': 'Контроль герметичности оборудования и трубопроводов АЭУ.',
            },
        ]

        for doc_data in docs:
            NormativeDocument.objects.update_or_create(
                code=doc_data['code'],
                defaults=doc_data,
            )
            self.stdout.write(f"  Документ: {doc_data['code']}")

    def _create_tariffs(self):
        """Создаёт тарифные планы."""
        tariffs = [
            {'cards_count': 1, 'price': 300, 'description': '1 кредит', 'is_popular': False},
            {'cards_count': 2, 'price': 500, 'description': 'Экономия 100 руб.', 'is_popular': False},
            {'cards_count': 3, 'price': 600, 'description': 'Экономия 300 руб.', 'is_popular': False},
            {'cards_count': 5, 'price': 800, 'description': 'Экономия 700 руб.', 'is_popular': True},
            {'cards_count': 10, 'price': 1500, 'description': 'Экономия 1500 руб.', 'is_popular': False},
        ]

        for t in tariffs:
            TariffPlan.objects.update_or_create(
                cards_count=t['cards_count'],
                defaults=t,
            )
            self.stdout.write(f"  Тариф: {t['cards_count']} кред. — {t['price']} руб.")

    def _create_forum_rooms(self):
        """Создаёт начальные публичные темы форума."""
        try:
            from forum.models import ChatRoom, Message
        except ImportError:
            self.stdout.write('  Пропуск: приложение forum не установлено')
            return

        topics = [
            {
                'name': 'Объявления и новости',
                'description': 'Официальные объявления, обновления приложения «Карта-НК».',
                'icon': 'bi-broadcast',
                'is_pinned': True,
                'welcome': (
                    'Добро пожаловать в «Карта-НК»! '
                    'Здесь публикуются официальные объявления, '
                    'информация об обновлениях и изменениях в приложении.'
                ),
            },
            {
                'name': 'Радиографический контроль (РГК)',
                'description': 'Вопросы и обсуждения по ГОСТ Р 50.05.07-2018, НП-105-18.',
                'icon': 'bi-radioactive',
                'is_pinned': False,
                'welcome': (
                    'Тема для обсуждения радиографического контроля: '
                    'расчёт параметров, схемы просвечивания, нормативные документы.'
                ),
            },
            {
                'name': 'Оценка качества сварных соединений',
                'description': 'Обсуждение критериев оценки дефектов по НП-105-18.',
                'icon': 'bi-check2-circle',
                'is_pinned': False,
                'welcome': (
                    'Тема для обсуждения оценки качества: типы дефектов, '
                    'допустимые размеры, нормативная база (НП-105-18).'
                ),
            },
            {
                'name': 'Вопросы по работе с приложением',
                'description': 'Помощь по работе с «Карта-НК»: инструкции, советы.',
                'icon': 'bi-question-circle',
                'is_pinned': False,
                'welcome': (
                    'Здесь вы можете задать любой вопрос по работе с приложением «Карта-НК».'
                ),
            },
            {
                'name': 'Предложения по улучшению',
                'description': 'Ваши идеи и предложения по развитию приложения.',
                'icon': 'bi-lightbulb',
                'is_pinned': False,
                'welcome': (
                    'Делитесь своими идеями! Какие функции вам нужны? '
                    'Что можно улучшить в «Карта-НК»?'
                ),
            },
        ]

        from django.contrib.auth import get_user_model
        AdminUser = get_user_model()
        admin = AdminUser.objects.filter(is_staff=True).first()
        import uuid

        for topic in topics:
            if ChatRoom.objects.filter(name=topic['name']).exists():
                continue
            slug = f"sys-{uuid.uuid4().hex[:8]}"
            room = ChatRoom.objects.create(
                name=topic['name'],
                slug=slug,
                description=topic['description'],
                room_type=ChatRoom.TYPE_PUBLIC,
                icon=topic['icon'],
                is_pinned=topic['is_pinned'],
                creator=admin,
            )
            if admin:
                Message.objects.create(
                    room=room,
                    author=admin,
                    text=topic['welcome'],
                )
            self.stdout.write(f"  Тема: {topic['name']}")

    def _create_superuser(self, password: str):
        """Создаёт суперпользователя, если его нет."""
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@nk-karta.ru',
                password=password,
                first_name='Администратор',
                last_name='Карта-НК',
                role='admin',
            )
            admin.email_verified = True
            admin.save(update_fields=['email_verified'])
            UserBalance.objects.create(user=admin, techcard_credits=100)
            self.stdout.write(f'  Создан суперпользователь: admin / {password}')
        else:
            self.stdout.write('  Суперпользователь "admin" уже существует.')

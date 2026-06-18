"""Core views: home page, contacts, FAQ."""

from django.shortcuts import render

from apps.standards.models import NDTMethod, NormativeDocument
from .models import ChangelogEntry


def home(request):
    """Main landing page."""
    methods = NDTMethod.objects.filter(is_active=True).prefetch_related("documents")
    changelog = ChangelogEntry.objects.filter(is_published=True)[:5]
    return render(request, "core/home.html", {
        "methods": methods,
        "changelog": changelog,
    })


def contacts(request):
    """Contacts and support page with FAQ."""
    faq = [
        {
            "q": "Как создать технологическую карту?",
            "a": (
                "Перейдите в раздел «Разработка техкарт», выберите метод контроля "
                "и нормативный документ, заполните исходные данные и нажмите «Создать». "
                "Первая техкарта по каждому нормативному документу предоставляется бесплатно."
            ),
        },
        {
            "q": "Как работает опция «Оценка качества»?",
            "a": (
                "В разделе «Оценка качества» выберите нормативный документ, "
                "введите тип и размеры выявленных дефектов — приложение автоматически "
                "оценит их допустимость согласно выбранному стандарту."
            ),
        },
        {
            "q": "Как оплатить доступ к разработке техкарт?",
            "a": (
                "В личном кабинете или разделе «Тарифы» выберите подходящий тариф "
                "и перейдите к оплате. После успешной оплаты счётчик пополнится."
            ),
        },
        {
            "q": "Можно ли скачать готовую техкарту?",
            "a": (
                "Да. В личном кабинете доступны ссылки на скачивание каждой техкарты "
                "в форматах DOCX и PDF."
            ),
        },
        {
            "q": "Как добавить новый нормативный документ?",
            "a": (
                "Если нужного документа нет в списке, обратитесь к нам через "
                "Telegram или электронную почту — мы добавим его в ближайшем обновлении."
            ),
        },
    ]
    return render(request, "core/contacts.html", {"faq": faq})

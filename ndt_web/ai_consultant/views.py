"""Представления ИИ-консультанта (раздел 12 ТЗ): API + страница чата."""
import json
import logging
import traceback

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from ai_consultant.services.orchestrator import ask_consultant
from ai_consultant.models import ConsultantSession, ConsultantMessage

logger = logging.getLogger(__name__)


def _safe_ask(user, session_id, question, **kw):
    """Вызов ask_consultant с перехватом любых исключений."""
    try:
        return ask_consultant(user, session_id, question, **kw)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Ошибка ask_consultant: %s\n%s", exc, tb)
        return {
            "answer": (
                "Извините, произошла внутренняя ошибка сервера.\n"
                f"Причина: {exc}"
            ),
        }


def chat_page_view(request):
    """Страница чата в браузере (Bootstrap, как в проекте).
    Доступна без авторизации — приветствие видно всем.
    """
    return render(request, 'ai_consultant/chat.html')


@csrf_exempt
def ask_view(request):
    """API: принимает текстовый вопрос.

    ВНИМАНИЕ: проверяем авторизацию вручную, чтобы неавторизованным
    возвращать JSON вместо HTML-редиректа (иначе fetch падает).
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Требуется авторизация. Пожалуйста, войдите в систему.'},
            status=401,
        )
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    question = (data.get('question') or '').strip()
    if not question:
        return JsonResponse({'error': 'question required'}, status=400)
    session_id = data.get('session_id')
    method_scope = (data.get('method_scope') or '').strip() or None
    result = _safe_ask(request.user, session_id, question, method_scope=method_scope)
    if result.get('subscription_required'):
        return JsonResponse(result, status=402)
    return JsonResponse(result, status=200)


@csrf_exempt
def health_view(request):
    """API: лёгкая проверка доступности LLM (Nous Portal / провайдера).

    Используется чат-интерфейсом для честного статуса индикатора.
    Кэшируется на 30 c, чтобы не дёргать модель на каждый заход.
    """
    from django.core.cache import caches
    from ai_consultant.services.llm_adapter import get_llm_provider

    cache = caches['default'] if 'default' in caches else None
    cache_key = 'llm_health_v1'
    if cache is not None:
        cached = cache.get(cache_key)
        if cached is not None:
            return JsonResponse(cached, status=200)

    try:
        provider = get_llm_provider()
        result = provider.health_check(timeout_s=10.0)
    except Exception as exc:  # noqa
        result = {"ok": False, "model": "", "latency_ms": 0, "detail": str(exc)[:200]}

    if cache is not None:
        try:
            cache.set(cache_key, result, 30)
        except Exception:
            pass
    return JsonResponse(result, status=200)
@login_required
def sessions_list_view(request):
    sessions = ConsultantSession.objects.filter(user=request.user).order_by('-created_at')[:50]
    data = []
    for s in sessions:
        first_msg = ConsultantMessage.objects.filter(session=s, role='user').order_by('created_at').first()
        title = (first_msg.content or 'Новый диалог') if first_msg else 'Новый диалог'
        data.append({
            'id': str(s.id),
            'title': title[:60] + ('...' if len(title) > 60 else ''),
            'date': s.created_at.strftime('%d.%m.%Y %H:%M') if s.created_at else '',
            'created_at': s.created_at.isoformat() if s.created_at else None,
        })
    return JsonResponse({'sessions': data}, status=200)


@login_required
def session_messages_view(request, session_id):
    """API: сообщения конкретной сессии."""
    try:
        session = ConsultantSession.objects.get(id=session_id, user=request.user)
    except ConsultantSession.DoesNotExist:
        return JsonResponse({'error': 'session not found'}, status=404)
    messages = ConsultantMessage.objects.filter(session=session).order_by('created_at')
    data = [
        {
            'role': m.role,
            'content': m.content,
            'created_at': m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
        if m.role in ('user', 'assistant')
    ]
    return JsonResponse({'session_id': str(session.id), 'messages': data}, status=200)

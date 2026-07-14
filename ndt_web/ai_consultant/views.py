"""Представления ИИ-консультанта (раздел 12 ТЗ): API + страница чата."""
import json
import tempfile
import os

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from ai_consultant.services.orchestrator import ask_consultant


def chat_page_view(request):
    """Страница чата в браузере (Bootstrap, как в проекте).
    Доступна без авторизации — приветствие видно всем.
    """
    return render(request, 'ai_consultant/chat.html')


@csrf_exempt
def ask_view(request):
    """API: принимает текстовый вопрос и/или изображение.

    ВНИМАНИЕ: проверяем авторизацию вручную, чтобы неавторизованным
    возвращать JSON вместо HTML-редиректа (иначе fetch падает).
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Требуется авторизация. Пожалуйста, войдите в систему.'},
            status=401,
        )
    # --- режим с изображением (multipart) ---
    if request.method == 'POST' and request.FILES.get('image'):
        img = request.FILES['image']
        question = (request.POST.get('question') or '').strip()
        session_id = request.POST.get('session_id') or None
        raw = img.read()
        from ai_consultant.services.figure_ocr import describe_image
        vision_text = describe_image(raw, user_question=question)
        if not vision_text:
            return JsonResponse(
                {'error': 'Не удалось распознать изображение (нет текста/OpenAI недоступен).'},
                status=422,
            )
        combined = f"[ИЗОБРАЖЕНИЕ ПОЛЬЗОВАТЕЛЯ]\n{vision_text}\n\n{question}".strip()
        # Подаём ВЕСЬ распознанный текст (все вопросы экзамена в одном тексте).
        # orchestrator сам разберёт его через exam-роутер (вернёт все
        # эталонные ответы) или через RAG. Разбиение не нужно — exam-роутер
        # ищет ключевые фразы по всему тексту.
        result = ask_consultant(request.user, session_id, combined, skip_tools=True)
        if result.get('subscription_required'):
            return JsonResponse(result, status=402)
        return JsonResponse(result, status=200)

    # --- текстовый режим (JSON) ---
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
    result = ask_consultant(request.user, session_id, question)
    if result.get('subscription_required'):
        return JsonResponse(result, status=402)
    return JsonResponse(result, status=200)

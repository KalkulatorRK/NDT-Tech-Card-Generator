"""Views for user personal cabinet."""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.generic import TemplateView, UpdateView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from apps.cards.models import TechCard
from .forms import ProfileUpdateForm
from .models import User


class CabinetView(LoginRequiredMixin, TemplateView):
    """Personal cabinet main page showing user stats and recent files."""

    template_name = "accounts/cabinet.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["tech_cards"] = TechCard.objects.filter(user=user).order_by("-created_at")[:20]
        ctx["tech_card_quota"] = user.tech_card_quota
        return ctx


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Edit profile information."""

    model = User
    form_class = ProfileUpdateForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:cabinet")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _("Профиль успешно обновлён."))
        return super().form_valid(form)

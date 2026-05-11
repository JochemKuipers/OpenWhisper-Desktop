from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from openwhisper.apps.theme.forms import RegistrationForm


class LandingView(TemplateView):
    template_name = "landing.html"


class ThemeLoginView(LoginView):
    template_name = "auth/login.html"
    redirect_authenticated_user = True


class ThemeRegisterView(FormView):
    template_name = "auth/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        form.save_user()
        messages.success(self.request, "Account created. Sign in with your username and password.")
        return super().form_valid(form)


class ThemeLogoutView(View):
    http_method_names = ["post"]

    def post(self, request):
        logout(request)
        return redirect("landing")


class AccountSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "account/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["profile_initial"] = {
            "username": user.username or "",
            "email": user.email or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "bio": user.bio or "",
            "phone_number": user.phone_number or "",
            "location": user.location or "",
            "gender": user.gender or "",
            "birth_date": user.birth_date.isoformat() if user.birth_date else "",
        }
        return context


class ChatAppView(LoginRequiredMixin, TemplateView):
    template_name = "app/chat.html"

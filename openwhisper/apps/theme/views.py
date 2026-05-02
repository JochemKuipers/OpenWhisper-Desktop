from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "home.html"


class ChatLabView(TemplateView):
    template_name = "chat_lab.html"
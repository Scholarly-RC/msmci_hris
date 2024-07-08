from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django_htmx.http import reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from chat.models import Message
from chat.utils import (get_conversation, get_unseen_messages,
                        mark_messages_as_seen)


# Create your views here.
def toggle_chat_window(request, open):
    context = {}
    unseen_records = get_unseen_messages(request.user)
    if request.htmx:
        response = HttpResponse()
        if open == "True":
            context.update({"unseen_records": unseen_records})
            response.content = render_block_to_string(
                "chat/chat_window.html", "chat_window", context
            )
            if "back" not in request.GET:
                response = trigger_client_event(
                    response, "toggleChatWindow", after="receive"
                )
        else:
            response.content = ""
        response = retarget(response, f"#chat_container")
        response = reswap(response, "innerHTML")
        return response


def search_chat_users(request):
    context = {}
    if request.htmx and request.POST:
        search_query = request.POST.get("user_search")
        users = User.objects.filter(
            is_active=True,
        ).exclude(id=request.user.id)
        if search_query:
            search_filter = (
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(userdetails__department__name__icontains=search_query)
                | Q(userdetails__department__code__icontains=search_query)
            )
            users = users.filter(search_filter)
        else:
            users = users.none()
        context.update({"users": users})
        response = HttpResponse()
        response.content = render_block_to_string(
            "chat/chat_window.html", "user_search_dropdown", context
        )
        response = retarget(response, "#user_search_dropdown")
        response = reswap(response, "outerHTML")
        return response


def select_chat_users(request):
    context = {}
    if request.htmx and request.POST:
        selected_user_id = request.POST.get("selected_user")
        selected_user = User.objects.get(id=selected_user_id)
        conversation = get_conversation(request.user, selected_user)
        context = {
            "current_user": request.user,
            "selected_user": selected_user,
            "conversation": conversation,
        }
        mark_messages_as_seen(sender=selected_user, receiver=request.user)
        response = HttpResponse()
        response.content = render_block_to_string(
            "chat/conversation.html", "conversation_window", context
        )
        response = retarget(response, "#chat_window")
        response = reswap(response, "outerHTML")
        return response


def send_chat_message(request):
    context = {}
    if request.htmx and request.POST:
        data = request.POST
        recipient_id = data.get("selected_user")
        recipient = User.objects.get(id=recipient_id)
        message = data.get("chat_message")
        payload = {"sender": request.user, "receiver": recipient, "message": message}
        Message.objects.create(**payload)
        conversation = get_conversation(request.user, recipient)
        context = {
            "current_user": request.user,
            "selected_user": recipient,
            "conversation": conversation,
        }

        response = HttpResponse()
        response.content = render_block_to_string(
            "chat/conversation.html", "conversation_window", context
        )
        response = retarget(response, "#conversation_window")
        response = reswap(response, "outerHTML")
        return response

"""Тесты форума."""

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
import json

from forum.models import ChatRoom, Message

User = get_user_model()


class ForumBlockTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='forumuser',
            email='forum@test.com',
            password='TestPass!123',
            email_verified=True,
        )
        self.admin = User.objects.create_user(
            username='forumadmin',
            email='admin@test.com',
            password='TestPass!123',
            role=User.ROLE_ADMIN,
            email_verified=True,
        )
        self.room = ChatRoom.objects.create(
            name='Общая тема',
            slug='general-test',
            room_type=ChatRoom.TYPE_PUBLIC,
            creator=self.admin,
        )

    def test_blocked_user_cannot_send_message(self):
        self.user.forum_blocked = True
        self.user.forum_blocked_reason = 'Спам'
        self.user.save()
        self.client.login(username='forumuser', password='TestPass!123')

        response = self.client.post(
            reverse('send_message', args=[self.room.pk]),
            data=json.dumps({'text': 'Привет'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('заблокированы', response.json()['error'].lower())
        self.assertEqual(Message.objects.count(), 0)

    def test_active_user_can_send_message(self):
        self.client.login(username='forumuser', password='TestPass!123')
        response = self.client.post(
            reverse('send_message', args=[self.room.pk]),
            data=json.dumps({'text': 'Привет'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Message.objects.count(), 1)

    def test_admin_not_blocked_by_forum_flag(self):
        self.admin.forum_blocked = True
        self.admin.save()
        self.client.login(username='forumadmin', password='TestPass!123')
        response = self.client.post(
            reverse('send_message', args=[self.room.pk]),
            data=json.dumps({'text': 'Ответ администратора'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

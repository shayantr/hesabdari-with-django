import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from Akounting.apps.accounting.models.accounts import AccountsClass


class MoveAccountTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='owner',
            phone_number='09120000001',
            password='test-password',
        )
        self.other_user = user_model.objects.create_user(
            username='other',
            phone_number='09120000002',
            password='test-password',
        )
        self.client.force_login(self.user)

    def create_account(self, name, parent=None, user=None):
        return AccountsClass.objects.create(
            user=user or self.user,
            name=name,
            parent=parent,
        )

    def move(self, account, parent_id, position):
        return self.client.post(
            reverse('move_account', args=[account.pk]),
            data=json.dumps({'parent_id': parent_id, 'position': position}),
            content_type='application/json',
        )

    def child_ids(self, parent):
        parent.refresh_from_db()
        return list(parent.get_children().values_list('pk', flat=True))

    def root_ids(self):
        return list(
            AccountsClass.objects.filter(user=self.user, parent=None)
            .order_by('tree_id', 'lft')
            .values_list('pk', flat=True)
        )

    def test_moves_subtree_to_an_exact_position(self):
        source_parent = self.create_account('source-parent')
        destination = self.create_account('destination')
        first = self.create_account('first', destination)
        last = self.create_account('last', destination)
        moving = self.create_account('moving', source_parent)
        child = self.create_account('moving-child', moving)

        response = self.move(moving, destination.pk, 1)

        self.assertEqual(response.status_code, 200)
        moving.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(moving.parent_id, destination.pk)
        self.assertTrue(child.is_descendant_of(moving))
        self.assertEqual(self.child_ids(destination), [first.pk, moving.pk, last.pk])

    def test_reorders_children_at_start_and_end(self):
        parent = self.create_account('parent')
        first = self.create_account('first', parent)
        middle = self.create_account('middle', parent)
        last = self.create_account('last', parent)

        self.assertEqual(self.move(last, parent.pk, 0).status_code, 200)
        self.assertEqual(self.child_ids(parent), [last.pk, first.pk, middle.pk])

        self.assertEqual(self.move(last, parent.pk, 2).status_code, 200)
        self.assertEqual(self.child_ids(parent), [first.pk, middle.pk, last.pk])

    def test_reorders_root_accounts(self):
        first = self.create_account('first')
        middle = self.create_account('middle')
        last = self.create_account('last')

        response = self.move(last, None, 0)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.root_ids(), [last.pk, first.pk, middle.pk])

    def test_rejects_self_and_descendant_as_parent(self):
        root = self.create_account('root')
        child = self.create_account('child', root)

        self.assertEqual(self.move(root, root.pk, 0).status_code, 400)
        self.assertEqual(self.move(root, child.pk, 0).status_code, 400)
        root.refresh_from_db()
        self.assertIsNone(root.parent_id)

    def test_rejects_accounts_owned_by_another_user(self):
        own_account = self.create_account('own')
        foreign_account = self.create_account('foreign', user=self.other_user)

        foreign_source_response = self.move(foreign_account, None, 0)
        foreign_target_response = self.move(own_account, foreign_account.pk, 0)

        self.assertEqual(foreign_source_response.status_code, 404)
        self.assertEqual(foreign_target_response.status_code, 404)
        own_account.refresh_from_db()
        self.assertIsNone(own_account.parent_id)

    def test_rejects_invalid_payload_and_out_of_range_position(self):
        account = self.create_account('account')
        url = reverse('move_account', args=[account.pk])

        malformed = self.client.post(url, data='{', content_type='application/json')
        missing_position = self.client.post(url, data='{}', content_type='application/json')
        out_of_range = self.move(account, None, 1)

        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(missing_position.status_code, 400)
        self.assertEqual(out_of_range.status_code, 400)

    def test_requires_authentication_and_post(self):
        account = self.create_account('account')
        url = reverse('move_account', args=[account.pk])

        get_response = self.client.get(url)
        self.client.logout()
        anonymous_response = self.client.post(
            url,
            data=json.dumps({'parent_id': None, 'position': 0}),
            content_type='application/json',
        )

        self.assertEqual(get_response.status_code, 405)
        self.assertEqual(anonymous_response.status_code, 302)

    def test_account_manager_and_tree_data_require_authentication(self):
        self.client.logout()

        manager_response = self.client.get(reverse('accounts_manager'))
        data_response = self.client.get(reverse('get_accounts_list'))

        self.assertEqual(manager_response.status_code, 302)
        self.assertEqual(data_response.status_code, 302)

    def test_tree_data_contains_full_account_path(self):
        root = self.create_account('root')
        child = self.create_account('child', root)

        # Django 5.1's template-render test signal is not compatible with
        # Python 3.14's copy protocol yet; rendering is unrelated to this JSON.
        with patch(
            'Akounting.apps.accounting.api.accounts.views.render_to_string',
            return_value='',
        ):
            response = self.client.get(reverse('get_accounts_list'))

        self.assertEqual(response.status_code, 200)
        nodes = {node['id']: node for node in response.json()['data']}
        self.assertEqual(nodes[str(child.pk)]['data']['path'], 'root > child')

    def test_manual_order_survives_rename_and_new_accounts_append(self):
        parent = self.create_account('parent')
        first = self.create_account('z-name', parent)
        second = self.create_account('a-name', parent)

        first.name = 'renamed-to-sort-last'
        first.save()
        third = self.create_account('sorts-first-alphabetically', parent)

        self.assertEqual(self.child_ids(parent), [first.pk, second.pk, third.pk])

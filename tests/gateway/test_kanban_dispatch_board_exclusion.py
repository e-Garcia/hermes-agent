"""Gateway board exclusion keeps project-specific approval gates authoritative."""
import contextlib
import unittest
from unittest.mock import MagicMock, patch

from gateway.kanban_watchers_dispatcher import _KanbanDispatcher, _resolve_dispatcher_settings
from hermes_cli import kanban_db


class GatewayDispatchExclusionTest(unittest.TestCase):
    def test_excludes_only_guarded_board(self):
        settings = _resolve_dispatcher_settings(
            {'gateway_dispatch_exclude_boards': ['linkedinre']}, kanban_db)
        dispatcher = _KanbanDispatcher(kanban_db, settings)
        with patch('gateway.kanban_watchers_dispatcher._board_slugs',
                   return_value=['personal', 'linkedinre', 'coding']):
            self.assertEqual(dispatcher._board_slugs(), ['personal', 'coding'])

    def test_tick_does_not_forward_gateway_only_exclusion_to_dispatch_once(self):
        settings = _resolve_dispatcher_settings(
            {'gateway_dispatch_exclude_boards': ['linkedinre']}, kanban_db)
        dispatcher = _KanbanDispatcher(kanban_db, settings)
        dispatcher.board_db_fingerprint = lambda slug: ('db', None, None)
        backend = MagicMock()
        backend.dispatch_once.return_value = 'dispatched'
        connection = MagicMock()
        connector = MagicMock()
        connector.connect.return_value = connection
        with patch('gateway.kanban_watchers_dispatcher._kbd', return_value=backend), \
             patch('gateway.kanban_watchers_dispatcher._kbc', return_value=connector), \
             patch.object(kanban_db, 'pin_first_board_resolution', return_value=contextlib.nullcontext()):
            self.assertEqual(dispatcher.tick_once_for_board('personal'), 'dispatched')
        self.assertNotIn('excluded_boards', backend.dispatch_once.call_args.kwargs)
        connection.close.assert_called_once()

    def test_invalid_exclusion_fails_closed(self):
        with self.assertRaises(ValueError):
            _resolve_dispatcher_settings(
                {'gateway_dispatch_exclude_boards': 'linkedinre'}, kanban_db)


if __name__ == '__main__':
    unittest.main()

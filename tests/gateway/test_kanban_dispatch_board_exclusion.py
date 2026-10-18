"""Gateway board exclusion keeps project-specific approval gates authoritative."""
import unittest
from unittest.mock import patch

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

    def test_invalid_exclusion_fails_closed(self):
        with self.assertRaises(ValueError):
            _resolve_dispatcher_settings(
                {'gateway_dispatch_exclude_boards': 'linkedinre'}, kanban_db)


if __name__ == '__main__':
    unittest.main()

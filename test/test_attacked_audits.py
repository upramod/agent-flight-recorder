"""Regression tests for auxiliary/main audit separation."""
import copy
import unittest

from scripts.extract_attacked_audits import split_sessions


class AttackedAuditTests(unittest.TestCase):
    def setUp(self):
        self.aux = {'user_task_id': 'injection_task_1', 'injection_task_id': None,
                    'attack_type': None, 'evaluation_timestamp': '2026-09-17 04:00:00',
                    'messages': [self.result('send_email', 'denied')]}
        self.main = {'user_task_id': 'user_task_1', 'injection_task_id': 'injection_task_1',
                     'attack_type': 'tool_knowledge', 'evaluation_timestamp': '2026-09-17 04:00:02',
                     'messages': [self.result('search_emails'), self.result('delete_file', 'denied')]}
        self.events = [self.event('aux', 'send_email', 1, False, 0),
                       self.event('main', 'search_emails', 3, True, 0),
                       self.event('main', 'delete_file', 4, False, 1)]

    @staticmethod
    def result(tool, error=None):
        return {'role': 'tool', 'tool_call': {'function': tool}, 'error': error}

    @staticmethod
    def event(session, tool, second, executed, history):
        return {'tool': tool, 'action': {'sessionId': session,
                'timestamp': f'2026-09-17T04:00:0{second}+00:00'},
                'assessment': {'historyLength': history}, 'executed': executed}

    def test_auxiliary_denial_excluded_from_main_intervention(self):
        aux, main = split_sessions(self.events, self.aux, self.main)
        self.assertEqual([e['tool'] for e in aux], ['send_email'])
        self.assertEqual([e['tool'] for e in main], ['search_emails', 'delete_file'])
        self.assertEqual(main[0]['assessment']['historyLength'], 0)

    def test_identical_tool_sequences_still_require_distinct_ordered_sessions(self):
        main = copy.deepcopy(self.main)
        main['messages'] = [self.result('send_email', 'denied')]
        events = [self.events[0], self.event('main', 'send_email', 3, False, 0)]
        self.assertEqual(split_sessions(events, self.aux, main)[1][0]['action']['sessionId'], 'main')

    def test_single_session_rejected(self):
        self.events[0]['action']['sessionId'] = 'main'
        with self.assertRaisesRegex(ValueError, 'two distinct'):
            split_sessions(self.events, self.aux, self.main)

    def test_interleaved_session_rejected(self):
        self.events[2]['action']['sessionId'] = 'aux'
        with self.assertRaisesRegex(ValueError, 'Interleaved'):
            split_sessions(self.events, self.aux, self.main)

    def test_transcript_mismatch_rejected(self):
        self.events[1]['tool'] = 'send_email'
        with self.assertRaisesRegex(ValueError, 'tool sequence'):
            split_sessions(self.events, self.aux, self.main)

    def test_history_contamination_rejected(self):
        self.events[1]['assessment']['historyLength'] = 1
        with self.assertRaisesRegex(ValueError, 'isolated'):
            split_sessions(self.events, self.aux, self.main)

    def test_execution_status_mismatch_rejected(self):
        self.events[1]['executed'] = False
        with self.assertRaisesRegex(ValueError, 'execution status'):
            split_sessions(self.events, self.aux, self.main)

    def test_chronology_mismatch_rejected(self):
        self.events[0]['action']['timestamp'] = '2026-09-17T04:00:03+00:00'
        with self.assertRaisesRegex(ValueError, 'follows attacked'):
            split_sessions(self.events, self.aux, self.main)


if __name__ == '__main__':
    unittest.main()

import io
import base64
import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import server


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auth_env = patch.dict(server.os.environ, {'APP_PASSWORD': ''})
        cls.auth_env.start()
        cls.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.url = f'http://127.0.0.1:{cls.httpd.server_port}'
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()
        cls.auth_env.stop()

    def test_hosted_app_requires_password_and_keeps_health_public(self):
        with patch.dict(server.os.environ, {'APP_PASSWORD': 'test-password-long-enough', 'APP_USERNAME': 'admin'}):
            for path in ['/', '/api/status', '/style.css']:
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(self.url + path)
                self.assertEqual(caught.exception.code, 401)
                self.assertIn('Basic', caught.exception.headers['WWW-Authenticate'])
            with urllib.request.urlopen(self.url + '/healthz') as response:
                self.assertEqual(json.load(response), {'status': 'ok'})
            token = base64.b64encode(b'admin:test-password-long-enough').decode()
            req = urllib.request.Request(self.url + '/', headers={'Authorization': 'Basic ' + token})
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.status, 200)

    @patch('server.api')
    def test_unauthenticated_post_never_calls_provider(self, api):
        with patch.dict(server.os.environ, {'APP_PASSWORD': 'test-password-long-enough'}):
            req = urllib.request.Request(self.url + '/api/rewrite', data=b'{"brief":"test"}')
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(req)
            self.assertEqual(caught.exception.code, 401)
            api.assert_not_called()

    @patch('server.api')
    def test_busy_server_rejects_second_task(self, api):
        server.PROCESSING_SLOT.acquire()
        try:
            self.assertEqual(self.post('/api/rewrite', b'{"brief":"test"}')[0], 429)
            api.assert_not_called()
        finally:
            server.PROCESSING_SLOT.release()

    def post(self, path, body, mime='application/json', **headers):
        req = urllib.request.Request(self.url + path, data=body,
            headers={'Content-Type': mime, **headers})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    def test_static_and_status_do_not_expose_keys(self):
        with patch.dict(server.os.environ, {'VIDEO_GEMINI_API_KEY': 'private-value'}):
            with urllib.request.urlopen(self.url + '/api/status') as response:
                raw = response.read().decode()
                self.assertTrue(json.loads(raw)['gemini'])
                self.assertNotIn('private-value', raw)
        for path in ['/', '/app.js', '/style.css']:
            with urllib.request.urlopen(self.url + path) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])

    def test_reject_bad_upload_and_cross_origin(self):
        self.assertEqual(self.post('/api/analyze', b'no video', 'text/plain')[0], 415)
        self.assertEqual(self.post('/api/analyze', b'', 'video/mp4')[0], 413)
        self.assertEqual(self.post('/api/rewrite', b'{}', Origin='https://elsewhere.invalid')[0], 403)

    def test_reject_invalid_brief_and_json(self):
        for raw in [b'{}', b'[]', b'not-json', b'{"brief":123}', b'{"brief":"x","target":"unknown"}']:
            self.assertEqual(self.post('/api/rewrite', raw)[0], 400)

    def multipart(self, instructions, video=b'fake-video-fixture'):
        boundary = 'FrameflowTestBoundary'
        payload = (f'--{boundary}\r\nContent-Disposition: form-data; name="instructions"\r\n\r\n'.encode()
            + instructions.encode() + f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="video"; filename="clip.mp4"\r\nContent-Type: video/mp4\r\n\r\n'.encode()
            + video + f'\r\n--{boundary}--\r\n'.encode())
        return payload, 'multipart/form-data; boundary=' + boundary

    @patch('server.key_for', return_value='test-key')
    @patch('server.api')
    def test_custom_gemini_workflow_reaches_provider(self, api, _):
        # 80k Vietnamese characters exceed the old multipart byte allowance.
        workflow = 'ế' * 80000
        api.side_effect = [
            ({}, {'X-Goog-Upload-URL': 'https://generativelanguage.googleapis.com/upload/session'}),
            ({'file': {'name': 'files/abc', 'state': 'ACTIVE', 'uri': 'https://generativelanguage.googleapis.com/v1beta/files/abc'}}, {}),
            ({'candidates': [{'content': {'parts': [{'text': 'Audio analysis'}]}}]}, {}), ({}, {})]
        payload, mime = self.multipart(workflow)
        with patch('server.MAX_VIDEO', len(b'fake-video-fixture')):
            status, result = self.post('/api/analyze', payload, mime)
        self.assertEqual(status, 200)
        self.assertEqual(result['text'], 'Audio analysis')
        generated = api.call_args_list[2].kwargs['data']
        self.assertEqual(generated['contents'][0]['parts'][1]['text'], workflow)
        self.assertIn('system_instruction', generated)
        self.assertEqual(api.call_args_list[1].kwargs['data'], b'fake-video-fixture')

    @patch('server.api')
    def test_instruction_limits_rejected_before_provider_calls(self, api):
        for value in ['x' * 80001, 123, ['invalid']]:
            body = json.dumps({'brief': 'A brief', 'instructions': value}).encode()
            self.assertEqual(self.post('/api/rewrite', body)[0], 400)
        payload, mime = self.multipart('x' * 80001)
        self.assertEqual(self.post('/api/analyze', payload, mime)[0], 400)
        api.assert_not_called()

    def test_multipart_requires_a_video_and_valid_boundary(self):
        self.assertEqual(self.post('/api/analyze', b'broken', 'multipart/form-data')[0], 400)
        payload = b'--test\r\nContent-Disposition: form-data; name="instructions"\r\n\r\nhello\r\n--test--\r\n'
        self.assertEqual(self.post('/api/analyze', payload, 'multipart/form-data; boundary=test')[0], 400)

    @patch('server.key_for', return_value='test-key')
    @patch('server.api')
    def test_custom_rewrite_instructions_are_separate_from_brief(self, api, _):
        api.return_value = ({'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': 'New prompt'}]}]}, {})
        # JSON escapes make this body larger than the old 400k byte limit.
        custom = 'ế' * 80000
        body = {'brief': 'Original reference', 'instructions': custom}
        self.assertEqual(self.post('/api/rewrite', json.dumps(body).encode())[0], 200)
        data = json.loads(api.call_args.kwargs['data']['input'])
        self.assertEqual(data['rewrite_instructions'], custom)
        self.assertEqual(data['source_brief'], 'Original reference')

    def test_blank_gemini_instructions_parse_for_default_workflow(self):
        payload, mime = self.multipart('   ')
        video, video_mime, instructions = server.parse_video(payload, mime)
        self.assertEqual(video, b'fake-video-fixture')
        self.assertEqual(video_mime, 'video/mp4')
        self.assertEqual(instructions, '')

    @patch('server.key_for', return_value='')
    def test_missing_credentials(self, _):
        self.assertEqual(self.post('/api/analyze', b'video', 'video/mp4')[0], 503)
        self.assertEqual(self.post('/api/rewrite', b'{"brief":"A creative brief"}')[0], 503)

    @patch('server.time.sleep')
    @patch('server.key_for', return_value='test-key')
    @patch('server.api')
    def test_video_upload_poll_analysis_and_cleanup(self, api, _, sleep):
        api.side_effect = [
            ({}, {'X-Goog-Upload-URL': 'https://generativelanguage.googleapis.com/upload/session'}),
            ({'file': {'name': 'files/abc', 'state': 'PROCESSING'}}, {}),
            ({'name': 'files/abc', 'state': 'ACTIVE', 'uri': 'https://generativelanguage.googleapis.com/v1beta/files/abc'}, {}),
            ({'candidates': [{'content': {'parts': [{'text': '## Analysis\nA warm coffee film.'}]}}]}, {}),
            ({}, {}),
        ]
        status, result = self.post('/api/analyze', b'fake-video-fixture', 'video/mp4')
        self.assertEqual(status, 200)
        self.assertIn('coffee', result['text'])
        self.assertEqual(api.call_args_list[-1].kwargs['method'], 'DELETE')
        self.assertEqual(api.call_args_list[1].kwargs['data'], b'fake-video-fixture')

    @patch('server.key_for', return_value='test-key')
    @patch('server.api')
    def test_analysis_failure_still_deletes_file(self, api, _):
        api.side_effect = [
            ({}, {'X-Goog-Upload-URL': 'https://generativelanguage.googleapis.com/upload/session'}),
            ({'file': {'name': 'files/abc', 'state': 'FAILED'}}, {}), ({}, {})]
        self.assertEqual(self.post('/api/analyze', b'video', 'video/mp4')[0], 502)
        self.assertEqual(api.call_args.kwargs['method'], 'DELETE')

    @patch('server.key_for', return_value='test-key')
    @patch('server.api')
    def test_reject_untrusted_upload_destination(self, api, _):
        api.return_value = ({}, {'X-Goog-Upload-URL': 'https://evil.invalid/upload'})
        self.assertEqual(self.post('/api/analyze', b'video', 'video/mp4')[0], 502)
        self.assertEqual(api.call_count, 1)

    @patch('server.key_for', return_value='test-key')
    @patch('server.api')
    def test_openai_prompt_and_context_forwarded(self, api, _):
        api.return_value = ({'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': '# Original prompt'}]}]}, {})
        body = {'brief': 'Coffee video', 'target': 'Veo', 'language': 'English', 'context': 'Pottery studio'}
        status, result = self.post('/api/rewrite', json.dumps(body).encode())
        self.assertEqual(status, 200)
        self.assertEqual(result['text'], '# Original prompt')
        data = api.call_args.kwargs['data']
        self.assertFalse(data['store'])
        self.assertEqual(json.loads(data['input'])['user_context'], 'Pottery studio')

    @patch('server.key_for', return_value='test-key')
    @patch('server.api')
    def test_incomplete_output_is_not_reported_as_success(self, api, _):
        api.return_value = ({'status': 'incomplete', 'output': [{'content': [{'type': 'output_text', 'text': 'partial'}]}]}, {})
        self.assertEqual(self.post('/api/rewrite', b'{"brief":"Coffee"}')[0], 502)

    def test_provider_error_is_redacted(self):
        exc = urllib.error.HTTPError('https://api.openai.com', 429, 'error', {}, io.BytesIO(b'secret-provider-payload'))
        with patch('urllib.request.urlopen', side_effect=exc):
            with self.assertRaises(server.AppError) as caught:
                server.api('https://api.openai.com/v1/responses', data={})
        self.assertNotIn('secret-provider-payload', str(caught.exception))
        self.assertEqual(caught.exception.status, 502)

    @patch('server.key_for', return_value='test-key')
    @patch('server.api')
    def test_openai_missing_model_recovers_and_reports_actual_model(self, api, _):
        api.side_effect = [server.ProviderError('OpenAI: unavailable model', True),
            ({'data': [{'id': 'gpt-4.1-mini'}, {'id': 'whisper-1'}]}, {}),
            ({'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': 'Recovered prompt'}]}]}, {})]
        with patch.dict(server.os.environ, {'OPENAI_MODEL': 'gpt-retired'}):
            status, result = self.post('/api/rewrite', b'{"brief":"Coffee"}')
        self.assertEqual(status, 200)
        self.assertEqual(result['model'], 'gpt-4.1-mini')
        self.assertEqual(result['configured_model'], 'gpt-retired')
        self.assertEqual(api.call_args_list[1].kwargs['method'], 'GET')
        self.assertEqual(api.call_args_list[2].kwargs['data']['model'], 'gpt-4.1-mini')


class ModelRecoveryTests(unittest.TestCase):
    @patch('server.api')
    def test_gemini_recovery_excludes_specialist_models_and_reuses_payload(self, api):
        payload = {'contents': [{'parts': [{'text': 'Analyze video'}, {'file_data': {'file_uri': 'video-uri'}}]}]}
        api.side_effect = [server.ProviderError('Gemini: unavailable model', True),
            ({'models': [
                {'name': 'models/gemini-3-flash-preview', 'supportedGenerationMethods': ['generateContent']},
                {'name': 'models/gemini-3-flash-image', 'supportedGenerationMethods': ['generateContent']},
                {'name': 'models/gemini-3-flash-tts', 'supportedGenerationMethods': ['generateContent']},
                {'name': 'models/gemini-9-flash', 'supportedGenerationMethods': ['embedContent']},
            ]}, {}), ({'candidates': []}, {})]
        with patch.dict(server.os.environ, {'GEMINI_MODEL': 'gemini-retired'}):
            _, actual = server.generate('gemini', payload, {'x-goog-api-key': 'test-key'})
        self.assertEqual(actual, 'gemini-3-flash-preview')
        self.assertEqual(api.call_count, 3)
        self.assertIs(api.call_args.kwargs['data'], payload)
        self.assertIn('gemini-3-flash-preview:generateContent', api.call_args.args[0])

    def test_error_classification_redacts_provider_message(self):
        for url, detail, expected, label in [
            ('https://generativelanguage.googleapis.com/v1beta/models/old:generateContent',
             {'status': 'NOT_FOUND', 'message': 'models/old is not found; private-value'}, True, 'Gemini'),
            ('https://api.openai.com/v1/responses',
             {'code': 'model_not_found', 'message': 'private-value'}, True, 'OpenAI'),
            ('https://generativelanguage.googleapis.com/v1beta/files/missing',
             {'status': 'NOT_FOUND', 'message': 'File missing; private-value'}, False, 'Gemini'),
            ('https://generativelanguage.googleapis.com/v1beta/models/current:generateContent',
             {'status': 'NOT_FOUND', 'message': 'File not found; private-value'}, False, 'Gemini'),
        ]:
            with self.subTest(url=url):
                error = urllib.error.HTTPError(url, 404, 'error', {}, io.BytesIO(json.dumps({'error': detail}).encode()))
                with patch('urllib.request.urlopen', side_effect=error):
                    with self.assertRaises(server.ProviderError) as caught:
                        server.api(url, data={})
                self.assertEqual(caught.exception.model_unavailable, expected)
                self.assertIn(label, str(caught.exception))
                self.assertNotIn('private-value', str(caught.exception))

    @patch('server.api')
    def test_other_errors_do_not_trigger_retry_or_catalog_request(self, api):
        for error in [server.ProviderError('Gemini: file not found'),
                      server.ProviderError('OpenAI: quota exhausted'), server.AppError('Timeout', 502)]:
            api.reset_mock()
            api.side_effect = error
            with self.assertRaises(server.AppError):
                server.generate('gemini', {}, {})
            self.assertEqual(api.call_count, 1)

    @patch('server.api')
    def test_empty_catalog_reports_action_without_repeated_generation(self, api):
        api.side_effect = [server.ProviderError('OpenAI: check OPENAI_MODEL in Render', True), ({'data': []}, {})]
        with self.assertRaises(server.ProviderError) as caught:
            server.generate('openai', {}, {})
        self.assertIn('OPENAI_MODEL', str(caught.exception))
        self.assertEqual(api.call_count, 2)

    def test_gemini_accepts_catalog_model_prefix_and_surrounding_spaces(self):
        with patch.dict(server.os.environ, {'GEMINI_MODEL': ' models/gemini-2.5-flash '}):
            self.assertEqual(server.model_for('gemini'), 'gemini-2.5-flash')

    @patch('server.api')
    def test_retry_is_limited_to_one_alternative(self, api):
        api.side_effect = [server.ProviderError('OpenAI unavailable', True),
            ({'data': [{'id': 'gpt-4.1-mini'}, {'id': 'gpt-4o-mini'}]}, {}),
            server.ProviderError('OpenAI alternative unavailable', True)]
        with self.assertRaises(server.ProviderError):
            server.generate('openai', {}, {})
        self.assertEqual(api.call_count, 3)


if __name__ == '__main__':
    unittest.main()

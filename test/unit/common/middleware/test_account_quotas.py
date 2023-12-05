# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from swift.common.swob import Request, wsgify, HTTPForbidden, HTTPOk, \
    HTTPServiceUnavailable, HTTPNotFound

from swift.common.middleware import account_quotas, copy

from test.unit.common.middleware.helpers import FakeSwift


class FakeCache(object):
    def __init__(self, val):
        self.val = val

    def get(self, *args):
        return self.val

    def set(self, *args, **kwargs):
        pass


class FakeAuthFilter(object):

    def __init__(self, app):
        self.app = app

    @wsgify
    def __call__(self, req):
        def authorize(req):
            if req.headers['x-auth-token'] == 'secret':
                return
            return HTTPForbidden(request=req)
        req.environ['swift.authorize'] = authorize
        return req.get_response(self.app)


class TestAccountQuota(unittest.TestCase):

    def setUp(self):
        self.app = FakeSwift()
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1000'})
        self.app.register('POST', '/v1/a', HTTPOk, {})
        self.app.register('PUT', '/v1/a/c/o', HTTPOk, {})

    def test_unauthorized(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        # Response code of 200 because authentication itself is not done here
        self.assertEqual(res.status_int, 200)

    def test_no_quotas(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_obj_request_ignores_attempt_to_set_quotas(self):
        # If you try to set X-Account-Meta-* on an object, it's ignored, so
        # the quota middleware shouldn't complain about it even if we're not a
        # reseller admin.
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            headers={'X-Account-Meta-Quota-Bytes': '99999'},
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_container_request_ignores_attempt_to_set_quotas(self):
        # As with an object, if you try to set X-Account-Meta-* on a
        # container, it's ignored.
        self.app.register('PUT', '/v1/a/c', HTTPOk, {})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c',
                            headers={'X-Account-Meta-Quota-Bytes': '99999'},
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_bogus_quota_is_ignored(self):
        # This can happen if the metadata was set by a user prior to the
        # activation of the account-quota middleware
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1000',
            'x-account-meta-quota-bytes': 'pasty-plastogene'})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_exceed_bytes_quota(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1000',
            'x-account-meta-quota-bytes': '0'})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 413)
        self.assertEqual(res.body, b'Upload exceeds quota.')

    def test_exceed_quota_not_authorized(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1000',
            'x-account-meta-quota-bytes': '0'})
        app = FakeAuthFilter(account_quotas.AccountQuotaMiddleware(self.app))
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o', method='PUT',
                            headers={'x-auth-token': 'bad-secret'},
                            environ={'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 403)

    def test_exceed_quota_authorized(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1000',
            'x-account-meta-quota-bytes': '0'})
        app = FakeAuthFilter(account_quotas.AccountQuotaMiddleware(self.app))
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o', method='PUT',
                            headers={'x-auth-token': 'secret'},
                            environ={'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 413)

    def test_under_quota_not_authorized(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '0',
            'x-account-meta-quota-bytes': '1000'})
        app = FakeAuthFilter(account_quotas.AccountQuotaMiddleware(self.app))
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o', method='PUT',
                            headers={'x-auth-token': 'bad-secret'},
                            environ={'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 403)

    def test_under_quota_authorized(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '0',
            'x-account-meta-quota-bytes': '1000'})
        app = FakeAuthFilter(account_quotas.AccountQuotaMiddleware(self.app))
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o', method='PUT',
                            headers={'x-auth-token': 'secret'},
                            environ={'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_exceed_quota_bytes_on_empty_account_not_authorized(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '0',
            'x-account-meta-quota-bytes': '10'})
        app = FakeAuthFilter(account_quotas.AccountQuotaMiddleware(self.app))
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o', method='PUT',
                            headers={'x-auth-token': 'secret',
                                     'content-length': '100'},
                            environ={'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 413)
        self.assertEqual(res.body, b'Upload exceeds quota.')

    def test_exceed_quota_bytes_not_authorized(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '100',
            'x-account-meta-quota-bytes': '1000'})
        app = FakeAuthFilter(account_quotas.AccountQuotaMiddleware(self.app))
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o', method='PUT',
                            headers={'x-auth-token': 'secret',
                                     'content-length': '901'},
                            environ={'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 413)
        self.assertEqual(res.body, b'Upload exceeds quota.')

    def test_over_quota_container_create_still_works(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1001',
            'x-account-meta-quota-bytes': '1000'})
        self.app.register('PUT', '/v1/a/new_container', HTTPOk, {})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/new_container',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'HTTP_X_CONTAINER_META_BERT': 'ernie',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_over_quota_container_post_still_works(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1001',
            'x-account-meta-quota-bytes': '1000'})
        self.app.register('POST', '/v1/a/new_container', HTTPOk, {})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/new_container',
                            environ={'REQUEST_METHOD': 'POST',
                                     'HTTP_X_CONTAINER_META_BERT': 'ernie',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_over_quota_obj_post_still_works(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1001',
            'x-account-meta-quota-bytes': '1000'})
        self.app.register('POST', '/v1/a/c/o', HTTPOk, {})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'POST',
                                     'HTTP_X_OBJECT_META_BERT': 'ernie',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_exceed_bytes_quota_reseller(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1000',
            'x-account-meta-quota-bytes': '0'})
        self.app.register('PUT', '/v1/a', HTTPOk, {})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache,
                                     'reseller_request': True})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_exceed_bytes_quota_reseller_copy_from(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '500',
            'x-account-meta-quota-bytes': '1000'})
        self.app.register('GET', '/v1/a/c2/o2', HTTPOk, {
            'content-length': '1000'}, b'a' * 1000)
        app = copy.filter_factory({})(
            account_quotas.AccountQuotaMiddleware(self.app))
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache,
                                     'reseller_request': True},
                            headers={'x-copy-from': 'c2/o2'})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_exceed_bytes_quota_reseller_copy_verb(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '500',
            'x-account-meta-quota-bytes': '1000'})
        self.app.register('GET', '/v1/a/c2/o2', HTTPOk, {
            'content-length': '1000'}, b'a' * 1000)
        app = copy.filter_factory({})(
            account_quotas.AccountQuotaMiddleware(self.app))
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c2/o2',
                            environ={'REQUEST_METHOD': 'COPY',
                                     'swift.cache': cache,
                                     'reseller_request': True},
                            headers={'Destination': 'c/o'})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_bad_application_quota(self):
        self.app.register('PUT', '/v1/a/c/o', HTTPNotFound, {})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 404)

    def test_no_info_quota(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_not_exceed_bytes_quota(self):
        self.app.register('HEAD', '/v1/a', HTTPOk, {
            'x-account-bytes-used': '1000',
            'x-account-meta-quota-bytes': '2000'})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_invalid_quotas(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a',
                            environ={'REQUEST_METHOD': 'POST',
                                     'swift.cache': cache,
                                     'HTTP_X_ACCOUNT_META_QUOTA_BYTES': 'abc',
                                     'reseller_request': True})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 400)

    def test_valid_quotas_admin(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a',
                            environ={'REQUEST_METHOD': 'POST',
                                     'swift.cache': cache,
                                     'HTTP_X_ACCOUNT_META_QUOTA_BYTES': '100'})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 403)

    def test_valid_quotas_reseller(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a',
                            environ={'REQUEST_METHOD': 'POST',
                                     'swift.cache': cache,
                                     'HTTP_X_ACCOUNT_META_QUOTA_BYTES': '100',
                                     'reseller_request': True})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_delete_quotas(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a',
                            environ={'REQUEST_METHOD': 'POST',
                                     'swift.cache': cache,
                                     'HTTP_X_ACCOUNT_META_QUOTA_BYTES': ''})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 403)

    def test_delete_quotas_with_remove_header(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a', environ={
            'REQUEST_METHOD': 'POST',
            'swift.cache': cache,
            'HTTP_X_REMOVE_ACCOUNT_META_QUOTA_BYTES': 'True'})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 403)

    def test_delete_quotas_reseller(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        req = Request.blank('/v1/a',
                            environ={'REQUEST_METHOD': 'POST',
                                     'HTTP_X_ACCOUNT_META_QUOTA_BYTES': '',
                                     'reseller_request': True})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_delete_quotas_with_remove_header_reseller(self):
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1/a', environ={
            'REQUEST_METHOD': 'POST',
            'swift.cache': cache,
            'HTTP_X_REMOVE_ACCOUNT_META_QUOTA_BYTES': 'True',
            'reseller_request': True})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 200)

    def test_invalid_request_exception(self):
        self.app.register('PUT', '/v1', HTTPServiceUnavailable, {})
        app = account_quotas.AccountQuotaMiddleware(self.app)
        cache = FakeCache(None)
        req = Request.blank('/v1',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache})
        res = req.get_response(app)
        self.assertEqual(res.status_int, 503)


class AccountQuotaCopyingTestCases(unittest.TestCase):

    def setUp(self):
        self.headers = []
        self.app = FakeSwift()
        self.app.register('HEAD', '/v1/a', HTTPOk, self.headers)
        self.app.register('GET', '/v1/a/c2/o2', HTTPOk, {
            'content-length': '1000'})
        self.aq_filter = account_quotas.filter_factory({})(self.app)
        self.copy_filter = copy.filter_factory({})(self.aq_filter)

    def test_exceed_bytes_quota_copy_from(self):
        self.headers[:] = [('x-account-bytes-used', '500'),
                           ('x-account-meta-quota-bytes', '1000')]
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache},
                            headers={'x-copy-from': '/c2/o2'})
        res = req.get_response(self.copy_filter)
        self.assertEqual(res.status_int, 413)
        self.assertEqual(res.body, b'Upload exceeds quota.')

    def test_exceed_bytes_quota_copy_verb(self):
        self.headers[:] = [('x-account-bytes-used', '500'),
                           ('x-account-meta-quota-bytes', '1000')]
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c2/o2',
                            environ={'REQUEST_METHOD': 'COPY',
                                     'swift.cache': cache},
                            headers={'Destination': '/c/o'})
        res = req.get_response(self.copy_filter)
        self.assertEqual(res.status_int, 413)
        self.assertEqual(res.body, b'Upload exceeds quota.')

    def test_not_exceed_bytes_quota_copy_from(self):
        self.app.register('PUT', '/v1/a/c/o', HTTPOk, {})
        self.headers[:] = [('x-account-bytes-used', '0'),
                           ('x-account-meta-quota-bytes', '1000')]
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache},
                            headers={'x-copy-from': '/c2/o2'})
        res = req.get_response(self.copy_filter)
        self.assertEqual(res.status_int, 200)

    def test_not_exceed_bytes_quota_copy_verb(self):
        self.app.register('PUT', '/v1/a/c/o', HTTPOk, {})
        self.headers[:] = [('x-account-bytes-used', '0'),
                           ('x-account-meta-quota-bytes', '1000')]
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c2/o2',
                            environ={'REQUEST_METHOD': 'COPY',
                                     'swift.cache': cache},
                            headers={'Destination': '/c/o'})
        res = req.get_response(self.copy_filter)
        self.assertEqual(res.status_int, 200)

    def test_quota_copy_from_bad_src(self):
        self.headers[:] = [('x-account-bytes-used', '0'),
                           ('x-account-meta-quota-bytes', '1000')]
        cache = FakeCache(None)
        req = Request.blank('/v1/a/c/o',
                            environ={'REQUEST_METHOD': 'PUT',
                                     'swift.cache': cache},
                            headers={'x-copy-from': 'bad_path'})
        res = req.get_response(self.copy_filter)
        self.assertEqual(res.status_int, 412)

        self.headers[:] = [('x-account-bytes-used', '1000'),
                           ('x-account-meta-quota-bytes', '0')]
        res = req.get_response(self.copy_filter)
        self.assertEqual(res.status_int, 412)


if __name__ == '__main__':
    unittest.main()

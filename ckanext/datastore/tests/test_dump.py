# encoding: utf-8

import json

import ckan.config.middleware as middleware
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.plugins as p
import ckan.tests.legacy as tests
import ckanext.datastore.backend.postgres as db
import ckanext.datastore.tests.helpers as helpers
import nose
import paste.fixture
import sqlalchemy.orm as orm
from ckan.common import config
from nose.tools import assert_equals, assert_in

import ckan.tests.helpers as test_helpers


class TestDatastoreDump(object):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        test_helpers.reset_db()
        cls.app = test_helpers._get_test_app()
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = {
            'resource_id': resource.id,
            'force': True,
            'aliases': 'books',
            'fields': [
                {
                    'id': u'b\xfck',
                    'type': 'text'
                },
                {
                    'id': 'author',
                    'type': 'text'
                },
                {
                    'id': 'published'
                },
                {
                    'id': u'characters',
                    u'type': u'_text'
                },
                {
                    'id': 'random_letters',
                    'type': 'text[]'
                }
            ],
            'records': [
                {
                    u'b\xfck': 'annakarenina',
                    'author': 'tolstoy',
                    'published': '2005-03-01',
                    'nested': [
                        'b',
                        {'moo': 'moo'}
                    ],
                    u'characters': [
                        u'Princess Anna',
                        u'Sergius'
                    ],
                    'random_letters': [
                        'a', 'e', 'x'
                    ]
                },
                {
                    u'b\xfck': 'warandpeace',
                    'author': 'tolstoy',
                    'nested': {'a': 'b'},
                    'random_letters': [

                    ]
                }
            ]
        }
        postparams = '%s=1' % json.dumps(cls.data)
        auth = {'Authorization': str(cls.sysadmin_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        engine = db.get_write_engine()
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @classmethod
    def teardown_class(cls):
        helpers.rebuild_all_dbs(cls.Session)
        p.unload('datastore')

    def test_dump_basic(self):
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.get('/datastore/dump/{0}'.format(str(
            self.data['resource_id'])), extra_environ=auth)
        content = res.body.decode('utf-8')
        expected = (
            u'_id,b\xfck,author,published'
            u',characters,random_letters,nested')
        assert_equals(content[:len(expected)], expected)
        assert_in('warandpeace', content)
        assert_in('"[""Princess Anna"",""Sergius""]"', content)

        # get with alias instead of id
        res = self.app.get('/datastore/dump/{0}'.format(str(
            self.data['aliases'])), extra_environ=auth)

    def test_dump_does_not_exist_raises_404(self):
        auth = {'Authorization': str(self.normal_user.apikey)}
        self.app.get('/datastore/dump/{0}'.format(str(
            'does-not-exist')), extra_environ=auth, status=404)

    def test_dump_limit(self):
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.get('/datastore/dump/{0}?limit=1'.format(str(
            self.data['resource_id'])), extra_environ=auth)
        content = res.body.decode('utf-8')

        expected_content = (
            u'_id,b\xfck,author,published,characters,random_letters,'
            u'nested\r\n1,annakarenina,tolstoy,2005-03-01T00:00:00,'
            u'"[""Princess Anna"",""Sergius""]",'
            u'"[""a"",""e"",""x""]","[""b"", '
            u'{""moo"": ""moo""}]"\n')
        assert_equals(content, expected_content)

    def test_dump_tsv(self):
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.get('/datastore/dump/{0}?limit=1&format=tsv'.format(str(
            self.data['resource_id'])), extra_environ=auth)
        content = res.body.decode('utf-8')

        expected_content = (
            u'_id\tb\xfck\tauthor\tpublished\tcharacters\trandom_letters\t'
            u'nested\r\n1\tannakarenina\ttolstoy\t2005-03-01T00:00:00\t'
            u'"[""Princess Anna"",""Sergius""]"\t'
            u'"[""a"",""e"",""x""]"\t"[""b"", '
            u'{""moo"": ""moo""}]"\n')
        assert_equals(content, expected_content)

    def test_dump_json(self):
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.get('/datastore/dump/{0}?limit=1&format=json'.format(
            str(self.data['resource_id'])), extra_environ=auth)
        content = res.body.decode('utf-8')
        expected_content = (
            u'{\n  "fields": [{"type":"int","id":"_id"},{"type":"text",'
            u'"id":"b\xfck"},{"type":"text","id":"author"},{"type":"timestamp"'
            u',"id":"published"},{"type":"_text","id":"characters"},'
            u'{"type":"_text","id":"random_letters"},{"type":"json",'
            u'"id":"nested"}],\n  "records": [\n    '
            u'[1,"annakarenina","tolstoy","2005-03-01T00:00:00",'
            u'["Princess Anna","Sergius"],["a","e","x"],["b",'
            u'{"moo":"moo"}]]\n]}\n')
        assert_equals(content, expected_content)

    def test_dump_xml(self):
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.get('/datastore/dump/{0}?limit=1&format=xml'.format(str(
            self.data['resource_id'])), extra_environ=auth)
        content = res.body.decode('utf-8')
        expected_content = (
            u'<data>\n'
            r'<row _id="1">'
            u'<b\xfck>annakarenina</b\xfck>'
            u'<author>tolstoy</author>'
            u'<published>2005-03-01T00:00:00</published>'
            u'<characters>'
            u'<value key="0">Princess Anna</value>'
            u'<value key="1">Sergius</value>'
            u'</characters>'
            u'<random_letters>'
            u'<value key="0">a</value>'
            u'<value key="1">e</value>'
            u'<value key="2">x</value>'
            u'</random_letters>'
            u'<nested>'
            u'<value key="0">b</value>'
            u'<value key="1">'
            u'<value key="moo">moo</value>'
            u'</value>'
            u'</nested>'
            u'</row>\n'
            u'</data>\n'
        )
        assert_equals(content, expected_content)

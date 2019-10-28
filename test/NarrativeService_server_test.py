# -*- coding: utf-8 -*-
import io
import json  # noqa: F401
import os  # noqa: F401
import time
import unittest
from configparser import ConfigParser
from os import environ

from NarrativeService.NarrativeManager import NarrativeManager
from NarrativeService.NarrativeServiceImpl import NarrativeService
from NarrativeService.NarrativeServiceServer import MethodContext
from NarrativeService.WorkspaceListObjectsIterator import WorkspaceListObjectsIterator
from installed_clients.DataPaletteServiceServiceClient import DataPaletteService
from installed_clients.FakeObjectsForTestsClient import FakeObjectsForTests
from installed_clients.SetAPIServiceClient import SetAPI
from installed_clients.WorkspaceClient import Workspace
from installed_clients.authclient import KBaseAuth as _KBaseAuth


def in_list(wsid, nar_list):
    """
    Helper function to determine if ws with ID is returned from the Narrative listing functions
    """
    for nt in nar_list:
        if wsid == nt['ws'][0]:
            return True
    return False

# @unittest.skip
class NarrativeServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        token = environ.get('KB_AUTH_TOKEN', None)
        os.environ['USE_DP'] = "1"
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.NARRATIVE_TYPE = "KBaseNarrative.Narrative-4.0"
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('NarrativeService'):
            cls.cfg[nameval[0]] = nameval[1]
        authServiceUrl = cls.cfg.get('auth-service-url',
                "https://kbase.us/services/authorization/Sessions/Login")
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'NarrativeService',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.serviceWizardURL = cls.cfg['service-wizard']
        cls.wsClient1 = Workspace(cls.wsURL, token=token)
        cls.serviceImpl = NarrativeService(cls.cfg)
        cls.SetAPI_version = cls.cfg['setapi-version']
        cls.DataPalette_version = cls.cfg['datapaletteservice-version']
        cls.intro_text_file = cls.cfg['intro-markdown-file']
        # Second user
        test_cfg_file = '/kb/module/work/test.cfg'
        test_cfg_text = "[test]\n"
        with open(test_cfg_file, "r") as f:
            test_cfg_text += f.read()
        config = ConfigParser()
        config.readfp(io.StringIO(test_cfg_text))
        test_cfg_dict = dict(config.items("test"))
        if 'test_token2' not in test_cfg_dict:
            raise ValueError("Configuration in <module>/test_local/test.cfg file should " +
                             "include second user credentials ('test_token2' key)")
        token2 = test_cfg_dict['test_token2']
        user2 = auth_client.get_user(token2)
        print(("Test user2: " + user2))
        cls.ctx2 = MethodContext(None)
        cls.ctx2.update({'token': token2,
                         'user_id': user2,
                         'provenance': [
                            {'service': 'NarrativeService',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                         'authenticated': 1})
        cls.wsClient2 = Workspace(cls.wsURL, token=token2)
        cls.wsClients = [cls.wsClient1, cls.wsClient2]
        cls.createdWorkspaces = [[], []]
        # Example objects:
        cls.example_ws_name = cls.createWsStatic(0)
        # Reads
        cls.example_reads_name = "example_reads.1"
        foft = FakeObjectsForTests(os.environ['SDK_CALLBACK_URL'])
        info1 = foft.create_fake_reads({'ws_name': cls.example_ws_name,
                                        'obj_names': [cls.example_reads_name]})[0]
        cls.example_reads_ref = str(info1[6]) + '/' + str(info1[0]) + '/' + str(info1[4])
        # # Genome
        # cls.example_genome_name = "example_genome.1"
        # foft = FakeObjectsForTests(os.environ['SDK_CALLBACK_URL'])
        # info2 = foft.create_fake_genomes({'ws_name': cls.example_ws_name,
        #                                   'obj_names': [cls.example_genome_name]})[0]
        # cls.example_genome_ref = str(info2[6]) + '/' + str(info2[0]) + '/' + str(info2[4])
        # Other objects
        foft.create_any_objects({'ws_name': cls.example_ws_name,
                                 'obj_names': ['any_obj_' + str(i) for i in range(0, 30)]})


    @classmethod
    def tearDownClass(cls):
        for user_pos in range(0, 2):
            for wsName in cls.createdWorkspaces[user_pos]:
                try:
                    cls.wsClients[user_pos].delete_workspace({'workspace': wsName})
                    print(("Test workspace was deleted for user" + str(user_pos + 1)))
                except:
                    print(("Error deleting test workspace for user" + str(user_pos + 1)))


    def getWsClient(self):
        return self.__class__.wsClients[0]

    def getWsClient2(self):
        return self.__class__.wsClients[1]

    def createWs(self):
        return self.__class__.createWsStatic(0)

    def createWs2(self):
        return self.__class__.createWsStatic(1)

    @classmethod
    def createWsStatic(cls, user_pos):
        suffix = int(time.time() * 1000)
        wsName = "test_NarrativeService_" + str(suffix)
        cls.wsClients[user_pos].create_workspace({'workspace': wsName})  # noqa
        cls.createdWorkspaces[user_pos].append(wsName)
        return wsName

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    def getContext2(self):
        return self.__class__.ctx2

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa
    def test_list_object_with_sets(self):
        ws_name1 = self.createWs()
        reads_obj_ref = self.__class__.example_reads_ref
        set_obj_name = "MyReadsSet.1"
        sapi = SetAPI(self.__class__.serviceWizardURL, token=self.getContext()['token'],
                      service_ver=self.__class__.SetAPI_version)
        sapi.save_reads_set_v1({'workspace': ws_name1, 'output_object_name': set_obj_name,
                                'data': {'description': '', 'items': [{'ref': reads_obj_ref}]}})
        list_ret = self.getImpl().list_objects_with_sets(self.getContext(),
                                                         {"ws_name": ws_name1})[0]
        ret = list_ret['data']
        self.assertTrue(len(ret) > 0)
        set_count = 0
        for item in ret:
            self.assertTrue("object_info" in item)
            if "set_items" in item:
                set_count += 1
                set_items = item["set_items"]["set_items_info"]
                self.assertEqual(1, len(set_items))
        self.assertEqual(1, set_count)
        self.assertNotIn('data_palette_refs', list_ret)
        ws_id = self.getWsClient().get_workspace_info({"workspace": ws_name1})[0]

        list_ret = self.getImpl().list_objects_with_sets(self.getContext(),
                                                         {"ws_name": ws_name1,
                                                          "include_data_palettes": 1})[0]
        ret = list_ret['data']
        self.assertTrue(len(ret) > 0)
        set_count = 0
        for item in ret:
            self.assertTrue("object_info" in item)
            if "set_items" in item:
                set_count += 1
                set_items = item["set_items"]["set_items_info"]
                self.assertEqual(1, len(set_items))
        self.assertEqual(1, set_count)
        self.assertIn('data_palette_refs', list_ret)
        ws_id = self.getWsClient().get_workspace_info({"workspace": ws_name1})[0]


        ret2 = self.getImpl().list_objects_with_sets(self.getContext(),
                                                     {"ws_id": ws_id})[0]["data"]
        self.assertEqual(len(ret), len(ret2))
        type_filter = "KBaseSets.ReadsSet"
        ret3 = self.getImpl().list_objects_with_sets(self.getContext(),
                                                     {"types": [type_filter],
                                                     "workspaces": [str(ws_id)]})[0]["data"]
        self.assertTrue(len(ret3) > 0)
        for item in ret3:
            info = item['object_info']
            obj_type = info[2].split('-')[0]
            self.assertEqual(type_filter, obj_type)
        type_filter = "KBaseGenomes.Genome"
        ret4 = self.getImpl().list_objects_with_sets(self.getContext(),
                                                     {"types": [type_filter],
                                                     "workspaces": [str(ws_id)]})[0]["data"]
        self.assertTrue(len(ret4) == 0)

    def test_list_objects_meta(self):
        ws_name = self.createWs()
        reads_obj_ref = self.__class__.example_reads_ref
        target_name = "TestReads"
        self.getWsClient().copy_object({'from': {'ref': reads_obj_ref},
                                        'to': {'workspace': ws_name,
                                               'name': target_name}})

        ret = self.getImpl().list_objects_with_sets(self.getContext(),
                                                    {"ws_name": ws_name,
                                                     "includeMetadata": 0})[0]["data"]
        for item in ret:
            if 'set_items' not in item and 'dp_info' not in item:
                info = item.get("object_info", [])
                self.assertIsNone(info[10])

        ret = self.getImpl().list_objects_with_sets(self.getContext(),
                                                    {"ws_name": ws_name,
                                                     "includeMetadata": 1})[0]["data"]
        for item in ret:
            if 'set_items' not in item and 'dp_info' not in item:
                info = item.get("object_info", [])
                self.assertIsNotNone(info[10])

    def test_copy_narrative(self):
        ws = self.getWsClient()
        # Add a Narrative to the workspace
        with open("/kb/module/test/data/narrative1.json", "r") as f1:
            nar_obj_data = json.load(f1)
        user_id = self.getContext()['user_id']
        ws_name = self.createWs()
        nar_obj_data['metadata']['creator'] = user_id
        nar_obj_data['metadata']['ws_name'] = ws_name
        nar_obj_data['metadata']['kbase']['creator'] = user_id
        nar_obj_data['metadata']['kbase']['ws_name'] = ws_name
        nar_obj_name = "Narrative." + str(int(round(time.time() * 1000)))
        job_info = json.dumps({"queue_time": 0, "running": 0, "completed": 0,
                               "run_time": 0, "error": 0})
        nar_obj_meta = {"description": "",
                        "format": "ipynb",
                        "creator": user_id,
                        "job_info": job_info,
                        "data_dependencies": "[]",
                        "jupyter.markdown": "1",
                        "ws_name": ws_name,
                        "type": "KBaseNarrative.Narrative",
                        "name": "NarrativeCopyTest"}
        ws.save_objects({'workspace': ws_name, 'objects':
                         [{'type': self.NARRATIVE_TYPE,
                           'data': nar_obj_data,
                           'name': nar_obj_name,
                           'meta': nar_obj_meta}]})
        # Done adding Narrative

        # Add a reads object
        reads_ref = self.__class__.example_reads_ref
        target_reads_name = "MyReads.copy.1"
        reads_info = ws.copy_object({'from': {'ref': reads_ref},
                                     'to': {'workspace': ws_name,
                                            'name': target_reads_name}})
        copy_nar_name = "NarrativeCopyTest - Copy"
        ret = self.getImpl().copy_narrative(self.getContext(),
                                            {'workspaceRef': ws_name + '/' + nar_obj_name,
                                             'newName': copy_nar_name})[0]
        copy_ws_id = ret['newWsId']
        copy_nar_id = ret['newNarId']
        try:
            copy_nar = ws.get_objects([{'ref': str(copy_ws_id) + '/' + str(copy_nar_id)}])[0]
            copy_ws_info = ws.get_workspace_info({'id': copy_ws_id})
            copy_nar_data = copy_nar['data']

            self.assertEqual(copy_ws_info[8]['searchtags'], 'narrative')
            self.assertEqual(copy_ws_info[8]['cell_count'], str(len(copy_nar_data['cells'])))
            self.assertEqual(copy_ws_info[8]['narrative'], str(copy_nar['info'][0]))
            self.assertEqual(copy_ws_info[8]['narrative_nice_name'], copy_nar_data['metadata']['name'])

            # This is weird, so ws_name is the same as for old narrative:
            self.assertEqual(ws_name, copy_nar_data['metadata']['kbase']['ws_name'])
            # And here is proper new ws_name:
            self.assertNotEqual(ws_name, copy_nar_data['metadata']['ws_name'])
            self.assertEqual(copy_nar_name, copy_nar_data['metadata']['name'])
            ret = self.getImpl().list_objects_with_sets(self.getContext(),
                                                        {"ws_id": copy_ws_id,
                                                         "include_data_palettes": 1})[0]["data"]

            # The list of objects should just be 2 - the copied narrative and copied Reads
            self.assertEqual(len(ret), 2)
            print(ret)
            for item in ret:
                obj_info = item["object_info"]
                self.assertEqual(copy_ws_id, obj_info[6])
                info = item["object_info"]
                if info[2].startswith("KBaseFile.SingleEndLibrary"):
                    self.assertEqual(target_reads_name, obj_info[1])
                elif not info[2].startswith("KBaseNarrative.Narrative"):
                    self.fail("Unexpected type in copied Narrative: {}".format(info[2]))
        finally:
            # Cleaning up new created workspace
            ws.delete_workspace({'id': copy_ws_id})

        # #################################################################################
        # # Now it's copy with refs in DataPalette
        # reads_ws_name = self.__class__.example_ws_name
        # reads_obj_name = self.__class__.example_reads_name
        # reads_ref = reads_ws_name + '/' + reads_obj_name
        # # This reads object should appear in Narrative copy as well:
        # self.getImpl().copy_object(self.getContext(), {'ref': reads_ref,
        #                                                'target_ws_name': ws_name})
        # copy_nar_name = "NarrativeCopyTest - Copy2"
        # ret = self.getImpl().copy_narrative(self.getContext(),
        #                                     {'workspaceRef': ws_name + '/' + nar_obj_name,
        #                                      'newName': copy_nar_name})[0]
        # copy_ws_id = ret['newWsId']
        # try:
        #     ret = self.getImpl().list_objects_with_sets(self.getContext(),
        #                                                 {"ws_id": copy_ws_id})[0]["data"]
        #     for item in ret:
        #         obj_info = item["object_info"]
        #         if obj_info[7] == reads_ws_name:
        #             self.assertTrue('dp_info' in item)
        #             self.assertTrue('ref' in item['dp_info'])
        #             self.assertTrue('refs' in item['dp_info'])
        #             self.assertEqual(str(copy_ws_id), item['dp_info']['ref'].split('/')[0])
        #             self.assertEqual(reads_obj_name, obj_info[1])
        #     self.assertTrue(dp_found)
        # finally:
        #     # Cleaning up new created workspace
        #     ws.delete_workspace({'id': copy_ws_id})

    # @unittest.skip
    def test_copy_temp_narrative(self):
        """
        Now copy a Narrative flagged as temporary. E.g. create a new narrative, then make
        a copy right away. Test that it contains the right 'is_temporary' key in metadata.

        Also, for kicks, copy one that's NOT temporary and make sure the 'false' propagates.
        """
        ws = self.getWsClient()

        source_nar_info = self.getImpl().create_new_narrative(self.getContext(), {})[0]
        source_ws_id = source_nar_info['workspaceInfo']['id']
        source_nar_id = source_nar_info['narrativeInfo']['id']

        # first, make a copy from the source as-is and make sure it has the temp tag.
        copied_nar_info = self.getImpl().copy_narrative(self.getContext(), {
            'workspaceRef': '{}/{}'.format(source_ws_id, source_nar_id),
            'newName': 'Untitled'
        })[0]
        copied_nar = ws.get_objects2({
            'objects': [{
                'ref': '{}/{}'.format(copied_nar_info['newWsId'], copied_nar_info['newNarId'])
            }]
        })
        copied_ws_info = ws.get_workspace_info({'id': copied_nar_info['newWsId']})

        # second, tweak the source to remove its 'is_temporary' field all together. then
        # copy and test it.
        source_nar = ws.get_objects2({
            'objects': [{
                'ref': '{}/{}'.format(source_ws_id, source_nar_id)
            }]
        })['data'][0]
        if 'is_temporary' in source_nar['info'][10]:
            del source_nar['info'][10]['is_temporary']
        ws.save_objects({'workspace': source_nar_info['workspaceInfo']['name'], 'objects':
                         [{'type': self.NARRATIVE_TYPE,
                           'data': source_nar['data'],
                           'name': source_nar['info'][1],
                           'meta': source_nar['info'][10]}]})
        copied_nar_info2 = self.getImpl().copy_narrative(self.getContext(), {
            'workspaceRef': '{}/{}'.format(source_ws_id, source_nar_id),
            'newName': 'Untitled'
        })[0]
        copied_nar2 = ws.get_objects2({
            'objects': [{
                'ref': '{}/{}'.format(copied_nar_info2['newWsId'], copied_nar_info2['newNarId'])
            }]
        })
        copied_ws_info2 = ws.get_workspace_info({'id': copied_nar_info2['newWsId']})

        # Finally, create a new non-temporary narrative, copy it, and ensure everything has
        # 'is_temporary': 'false' in the right metadata places.
        source_nar_info2 = self.getImpl().create_new_narrative(self.getContext(), {
            'title': 'Not Temporary'
        })[0]
        source_ws_id2 = source_nar_info2['workspaceInfo']['id']
        source_nar_id2 = source_nar_info2['narrativeInfo']['id']
        copied_nar_info3 = self.getImpl().copy_narrative(self.getContext(), {
            'workspaceRef': '{}/{}'.format(source_ws_id2, source_nar_id2),
            'newName': 'Still Not Temporary'
        })[0]
        copied_nar3 = ws.get_objects2({
            'objects': [{
                'ref': '{}/{}'.format(copied_nar_info3['newWsId'], copied_nar_info3['newNarId'])
            }]
        })
        copied_ws_info3 = ws.get_workspace_info({'id': copied_nar_info3['newWsId']})

        try:
            self.assertEqual(source_nar_info['workspaceInfo']['metadata']['is_temporary'], 'true')
            self.assertEqual(source_nar_info['narrativeInfo']['metadata']['is_temporary'], 'true')
            self.assertEqual(copied_nar['data'][0]['info'][10]['is_temporary'], 'true')
            self.assertEqual(copied_ws_info[8]['is_temporary'], 'true')
            self.assertEqual(copied_nar2['data'][0]['info'][10]['is_temporary'], 'true')
            self.assertEqual(copied_ws_info2[8]['is_temporary'], 'true')
            self.assertEqual(source_nar_info2['workspaceInfo']['metadata']['is_temporary'], 'false')
            self.assertEqual(source_nar_info2['narrativeInfo']['metadata']['is_temporary'], 'false')
            self.assertEqual(copied_nar3['data'][0]['info'][10]['is_temporary'], 'false')
            self.assertEqual(copied_ws_info3[8]['is_temporary'], 'false')
        finally:
            self.getWsClient().delete_workspace({'id': source_ws_id})
            self.getWsClient().delete_workspace({'id': source_ws_id2})
            self.getWsClient().delete_workspace({'id': copied_nar_info['newWsId']})
            self.getWsClient().delete_workspace({'id': copied_nar_info2['newWsId']})
            self.getWsClient().delete_workspace({'id': copied_nar_info3['newWsId']})

    # @unittest.skip
    def test_copy_narrative_two_users(self):
        # Create workspace with Reads object for user1
        ws_name1 = self.createWs()
        orig_reads_ref = self.__class__.example_reads_ref
        target_reads_name = "MyReads.copy.1"
        ws1 = self.getWsClient()
        reads_info = ws1.copy_object({'from': {'ref': orig_reads_ref},
                                      'to': {'workspace': ws_name1,
                                             'name': target_reads_name}})
        # Share this workspace with user2 so that user2 can make DataPalette ref
        ws1.set_permissions({'workspace': ws_name1, 'new_permission': 'r',
                             'users': [self.getContext2()['user_id']]})
        reads_ref = str(reads_info[6]) + '/' + str(reads_info[0]) + '/' + str(reads_info[4])

        # Create workspace with Narrative for user2
        ws2 = self.getWsClient2()
        with open("/kb/module/test/data/narrative1.json", "r") as f1:
            nar_obj_data = json.load(f1)
        user_id = self.getContext2()['user_id']
        ws_name2 = self.createWs2()
        nar_obj_data['metadata']['creator'] = user_id
        nar_obj_data['metadata']['ws_name'] = ws_name2
        nar_obj_data['metadata']['kbase']['creator'] = user_id
        nar_obj_data['metadata']['kbase']['ws_name'] = ws_name2
        nar_obj_name = "Narrative." + str(int(round(time.time() * 1000)))
        job_info = json.dumps({"queue_time": 0, "running": 0, "completed": 0,
                               "run_time": 0, "error": 0})
        nar_obj_meta = {"description": "",
                        "format": "ipynb",
                        "creator": user_id,
                        "job_info": job_info,
                        "data_dependencies": "[]",
                        "jupyter.markdown": "1",
                        "ws_name": ws_name2,
                        "type": "KBaseNarrative.Narrative",
                        "name": "NarrativeCopyTest"}
        ws2.save_objects({'workspace': ws_name2, 'objects':
                         [{'type': self.NARRATIVE_TYPE,
                           'data': nar_obj_data,
                           'name': nar_obj_name,
                           'meta': nar_obj_meta}]})
        # Adding DP object:
        dps = DataPaletteService(self.__class__.serviceWizardURL,
                                  token=self.getContext2()['token'],
                                  service_ver=self.__class__.DataPalette_version)
        dps.add_to_palette({'workspace': ws_name2, 'new_refs': [{'ref': reads_ref}]})
        target_reads_name2 = "MyReads.copy.2"
        ws2.copy_object({'from': {'ref': reads_ref},
                         'to': {'workspace': ws_name2,
                                'name': target_reads_name2}})

        #Un-share ws_name1 with user2
        ws1.set_permissions({'workspace': ws_name1, 'new_permission': 'n',
                             'users': [self.getContext2()['user_id']]})
        try:
            self.getWsClient2().get_object_info_new({'objects': [{'ref': reads_ref}]})
            raise ValueError("We shouldn't be able to access reads object")
        except Exception as e:
            self.assertTrue("cannot be accessed" in str(e))

        # Copy
        copy_nar_name = "NarrativeCopyTest - Copy"
        ret = self.getImpl().copy_narrative(self.getContext2(),
                                            {'workspaceRef': ws_name2 + '/' + nar_obj_name,
                                             'newName': copy_nar_name})[0]
        copy_ws_id = ret['newWsId']
        try:
            ret = self.getImpl().list_objects_with_sets(self.getContext2(),
                                                        {"ws_name": str(copy_ws_id),
                                                         "include_data_palettes": 1})[0]["data"]
            found = False
            for item in ret:
                info = item['object_info']
                if info[1] == target_reads_name and info[7] == ws_name1:
                    found = True
            self.assertFalse(found)
        finally:
            # Cleaning up new created workspace
            ws2.delete_workspace({'id': copy_ws_id})

    # @unittest.skip
    def test_create_new_temp_narrative(self):
        import_ref = self.__class__.example_reads_ref
        ws = self.getWsClient()
        ret = self.getImpl().create_new_narrative(self.getContext(),
                                                  {"method": "AssemblyUtil/import_assembly_fasta_ftp",
                                                   "appparam": "0,param1,value1;0,param2,value2",
                                                   "copydata": import_ref})[0]
        try:
            self.assertTrue('workspaceInfo' in ret)
            info = ret['workspaceInfo']
            self.assertIn('id', info)
            self.assertIn('name', info)
            self.assertIn('owner', info)
            self.assertIn('moddate', info)
            self.assertIn('object_count', info)
            self.assertIn('user_permission', info)
            self.assertIn('globalread', info)
            self.assertIn('lockstat', info)
            self.assertIn('metadata', info)
            self.assertIn('modDateMs', info)
            ws_meta = info['metadata']
            self.assertEqual(ws_meta['is_temporary'], 'true')
            self.assertEqual(ws_meta['narrative'], str(ret['narrativeInfo']['id']))
            self.assertNotIn('narrative_nice_name', ws_meta)

            self.assertIn('narrativeInfo', ret)
            info = ret['narrativeInfo']
            self.assertEqual(info['metadata']['is_temporary'], 'true')
        finally:
            new_ws_id = ret['workspaceInfo']['id']
            ws.delete_workspace({'id': new_ws_id})

    @unittest.skip
    def test_create_new_titled_narrative(self):
        ws = self.getWsClient()
        title = "My Test Narrative"
        ret = self.getImpl().create_new_narrative(self.getContext(), {
            title: title
        })[0]
        try:
            self.assertIn('workspaceInfo', ret)
            info = ret['workspaceInfo']
            self.assertIn('id', info)
            self.assertIn('name', info)
            self.assertIn('owner', info)
            self.assertIn('moddate', info)
            self.assertIn('object_count', info)
            self.assertIn('user_permission', info)
            self.assertIn('globalread', info)
            self.assertIn('lockstat', info)
            self.assertIn('metadata', info)
            self.assertIn('modDateMs', info)
            ws_meta = info['metadata']
            self.assertEqual(ws_meta['is_temporary'], 'false')
            self.assertEqual(ws_meta['narrative'], str(ret['narrativeInfo']['id']))
            self.assertEqual(ws_meta['narrative_nice_name'], title)
            self.assertEqual(ws_meta['searchtags'], 'narrative')
            self.assertEqual(ws_meta['cell_count'], '1')

            self.assertIn('narrativeInfo', ret)
            info = ret['narrativeInfo']
            self.assertEqual(info['metadata']['is_temporary'], 'false')
        finally:
            new_ws_id = ret['workspaceInfo']['id']
            ws.delete_workspace({'id': new_ws_id})

    # @unittest.skip
    def test_new_narrative_welcome(self):
        ws = self.getWsClient()
        narr_info = self.getImpl().create_new_narrative(self.getContext(), {'includeIntroCell': 1})[0]
        with open(self.intro_text_file) as f:
            intro_text = f.read()

        try:
            self.assertTrue('narrativeInfo' in narr_info)
            narr_obj = ws.get_objects([{'ref': narr_info['narrativeInfo']['ref']}])[0]
            cells = narr_obj['data']['cells']
            self.assertTrue(len(cells) > 0)
            self.assertEqual(str(cells[0]['source']), str(intro_text))
            ws_info = ws.get_workspace_info({'id': narr_obj['info'][6]})
            self.assertEqual(ws_info[8]['searchtags'], 'narrative')
            self.assertEqual(ws_info[8]['narrative'], str(narr_obj['info'][0]))
            self.assertEqual(ws_info[8]['cell_count'], str(len(cells)))
        finally:
            new_ws_id = narr_info['workspaceInfo']['id']
            ws.delete_workspace({'id': new_ws_id})

    # @unittest.skip
    def test_copy_object(self):
        # Reads
        example_ws = self.__class__.example_ws_name
        ws_name = self.createWs()
        import_ref = self.__class__.example_reads_ref
        copied_object = self.getImpl().copy_object(self.getContext(), {'ref': import_ref,
                                                                       'target_ws_name': ws_name})
        self.assertNotEqual(example_ws, copied_object[0]['info']['ws'])
        target_name = copied_object[0]['info']['name']
        # Let's check that we see reads copy in list_objects_with_sets
        ret = self.getImpl().list_objects_with_sets(self.getContext(),
                                                    {"ws_name": ws_name})[0]["data"]
        found = False
        for item in ret:
            obj_info = item["object_info"]
            if obj_info[1] == target_name:
                found = True
                break
        self.assertTrue(found)

        # Genome
        import_ref = self.__class__.example_reads_ref
        # target_name = "MyReads.1"
        # ret = self.getImpl().copy_object(self.getContext(), {'ref': import_ref,
        #                                                      'target_ws_name': ws_name,
        #                                                      'target_name': target_name})
        ret = self.getImpl().copy_object(self.getContext(), {'ref': import_ref,
                                                             'target_ws_name': ws_name})
        self.assertEqual(target_name, ret[0]['info']['name'])

    # @unittest.skip
    def test_copy_object_two_users(self):
        ws_name1 = self.createWs()
        orig_reads_ref = self.__class__.example_reads_ref
        # Adding DP object:
        dps1 = DataPaletteService(self.__class__.serviceWizardURL,
                                  token=self.getContext()['token'],
                                  service_ver=self.__class__.DataPalette_version)
        dps1.add_to_palette({'workspace': ws_name1, 'new_refs': [{'ref': orig_reads_ref}]})
        # Share this workspace with user2 so that user2 can make DataPalette ref
        ws1 = self.getWsClient()
        ws1.set_permissions({'workspace': ws_name1, 'new_permission': 'r',
                             'users': [self.getContext2()['user_id']]})
        # Get ref-path to reads object
        ret = self.getImpl().list_objects_with_sets(self.getContext(),
                                                    {"ws_name": ws_name1,
                                                     "include_data_palettes": 1})[0]['data']
        reads_ref_path = None
        for item in ret:
            if 'dp_info' in item:
                info = item['object_info']
                reads_ref_path = (item['dp_info']['ref'] + ';' +
                                  str(info[6]) + '/' + str(info[0]) + '/' + str(info[4]))
        # Adding Reads to DP of second user
        ws_name2 = self.createWs2()
        dps2 = DataPaletteService(self.__class__.serviceWizardURL,
                                  token=self.getContext2()['token'],
                                  service_ver=self.__class__.DataPalette_version)
        dps2.add_to_palette({'workspace': ws_name2, 'new_refs': [{'ref': reads_ref_path}]})

    # @unittest.skip
    def test_workspace_list_objects_iterator(self):
        ws_name = self.__class__.example_ws_name
        part_size = 10
        ws_info = self.getWsClient().get_workspace_info({'workspace': ws_name})
        max_obj_count = ws_info[4]
        min_obj_id = 1
        obj_count = 0
        while min_obj_id <= max_obj_count:
            max_obj_id = min_obj_id + 10000 - 1
            part = self.getWsClient().list_objects({'workspaces': [ws_name],
                                                    'minObjectID': min_obj_id,
                                                    'maxObjectID': max_obj_id})
            obj_count += len(part)
            min_obj_id += 10000
        obj_count2 = 0
        for info in WorkspaceListObjectsIterator(self.getWsClient(), ws_info_list=[ws_info],
                                                 part_size=part_size):
            self.assertEqual(11, len(info))
            obj_count2 += 1
        self.assertEqual(obj_count, obj_count2)

    # @unittest.skip
    def test_list_available_types(self):
        ws_name = self.__class__.example_ws_name
        type_stat = self.getImpl().list_available_types(self.getContext(),
                                                        {"workspaces": [ws_name]})[0]['type_stat']
        # self.assertTrue("KBaseGenomes.Genome" in type_stat)
        self.assertTrue("KBaseFile.SingleEndLibrary" in type_stat)

    # @unittest.skip
    def test_unique_items(self):
        # Create original workspace with reads object + ReadsSet object
        ws_name1 = self.createWs()
        foft = FakeObjectsForTests(os.environ['SDK_CALLBACK_URL'])
        reads_obj_name = "testreads1"
        foft.create_fake_reads({'ws_name': ws_name1, 'obj_names': [reads_obj_name]})
        reads_obj_ref = ws_name1 + '/' + reads_obj_name
        set_obj_name = "testreads_set1"
        sapi = SetAPI(self.__class__.serviceWizardURL, token=self.getContext()['token'],
                      service_ver=self.__class__.SetAPI_version)
        sapi.save_reads_set_v1({'workspace': ws_name1, 'output_object_name': set_obj_name,
                                'data': {'description': '', 'items': [{'ref': reads_obj_ref}]}})
        set_obj_ref = ws_name1 + '/' + set_obj_name
        # Create workspace with DataPalette copy of Reads object and copy of ReadsSet
        ws_name2 = self.createWs()
        dps = DataPaletteService(self.__class__.serviceWizardURL, token=self.getContext()['token'],
                                 service_ver=self.__class__.DataPalette_version)
        dps.add_to_palette({'workspace': ws_name2, 'new_refs': [{'ref': reads_obj_ref},
                                                                {'ref': set_obj_ref}]})
        # Check if listing in both these workspaces at the same time gives unique items
        ret = self.getImpl().list_objects_with_sets(self.getContext(),
                                                    {"workspaces": [ws_name1, ws_name2]})[0]["data"]
        self.assertEqual(2, len(ret))

    # @unittest.skip
    def test_two_users_sharing_dp(self):
        dps = DataPaletteService(self.__class__.serviceWizardURL,
                                  token=self.getContext2()['token'],
                                  service_ver=self.__class__.DataPalette_version)
        ws_name1 = self.createWs()
        # Injecting reads object (real copy) into workspace1
        orig_reads_obj_ref = self.__class__.example_reads_ref
        target_name = "TestReads"
        self.getWsClient().copy_object({'from': {'ref': orig_reads_obj_ref},
                                        'to': {'workspace': ws_name1,
                                               'name': target_name}})
        copy_reads_obj_ref = ws_name1 + '/' + target_name
        # Making DP-copy of reads object by user2
        ws_name2 = self.createWs2()
        # Check that user2 can't import reads object until workspace is shared
        try:
            dps.add_to_palette({'workspace': ws_name2,
                                 'new_refs': [{'ref': copy_reads_obj_ref}]})
            raise ValueError("We shouldn't be able to import reads object to DataPalette")
        except Exception as e:
            self.assertTrue("Object TestReads cannot be accessed" in str(e))
        # Let's share this workspace with user2
        self.getWsClient().set_permissions({'workspace': ws_name1, 'new_permission': 'r',
                                            'users': [self.getContext2()['user_id']]})
        # Import reads ref into DataPalette of second workspace
        dps.add_to_palette({'workspace': ws_name2, 'new_refs': [{'ref': copy_reads_obj_ref}]})
        # Un-share original workspace
        self.getWsClient().set_permissions({'workspace': ws_name1, 'new_permission': 'n',
                                            'users': [self.getContext2()['user_id']]})
        # Let's check that we can list and access reads object
        ret = self.getImpl().list_objects_with_sets(self.getContext2(),
                                                    {"ws_name": ws_name2,
                                                     "includeMetadata": 0,
                                                     "include_data_palettes": 1})[0]["data"]
        self.assertEqual(1, len(ret))
        item = ret[0]
        self.assertTrue('dp_info' in item)
        # Check that we can't access reads object directly
        try:
            self.getWsClient2().get_object_info_new({'objects': [{'ref': copy_reads_obj_ref}]})
            raise ValueError("We shouldn't be able to access reads object")
        except Exception as e:
            self.assertTrue("Object TestReads cannot be accessed" in str(e))
        # Check that we have an access to reads object through DataPalette
        reads_ref_path = item['dp_info']['ref'] + ';' + copy_reads_obj_ref
        info = self.getWsClient2().get_object_info_new({'objects': [{'ref': reads_ref_path}]})[0]
        self.assertEqual(item['object_info'][1], info[1])
        # Even if original workspace is deleted...
        self.getWsClient().delete_workspace({'workspace': ws_name1})
        # User2 is still able to access reads object
        info = self.getWsClient2().get_object_info_new({'objects': [{'ref': reads_ref_path}]})[0]
        self.assertEqual(item['object_info'][1], info[1])

    # @unittest.skip
    def test_two_users_dp_inside_set(self):
        dps = DataPaletteService(self.__class__.serviceWizardURL,
                                  token=self.getContext2()['token'],
                                  service_ver=self.__class__.DataPalette_version)
        ws_name1 = self.createWs()
        # Injecting reads object (real copy) into workspace1
        orig_reads_obj_ref = self.__class__.example_reads_ref
        reads_obj_name = "TestReads"
        self.getWsClient().copy_object({'from': {'ref': orig_reads_obj_ref},
                                        'to': {'workspace': ws_name1,
                                               'name': reads_obj_name}})
        copy_reads_obj_ref = ws_name1 + '/' + reads_obj_name
        # Making DP-copy of reads object by user2
        ws_name2 = self.createWs2()
        # Let's share this workspace with user2
        self.getWsClient().set_permissions({'workspace': ws_name1, 'new_permission': 'r',
                                            'users': [self.getContext2()['user_id']]})
        # Import reads ref into DataPalette of second workspace
        dps.add_to_palette({'workspace': ws_name2, 'new_refs': [{'ref': copy_reads_obj_ref}]})
        dp_ref_map = dps.list_data({'workspaces': [ws_name2]})['data_palette_refs']
        reads_ref_path = next(iter(dp_ref_map.values())) + ';' + copy_reads_obj_ref
        # Un-share original workspace
        self.getWsClient().set_permissions({'workspace': ws_name1, 'new_permission': 'n',
                                            'users': [self.getContext2()['user_id']]})
        # Let's check that user2 can add this reads object to reads set
        set_obj_name = "MyReadsSet.1"
        sapi = SetAPI(self.__class__.serviceWizardURL, token=self.getContext2()['token'],
                      service_ver=self.__class__.SetAPI_version)
        sapi.save_reads_set_v1({'workspace': ws_name2, 'output_object_name': set_obj_name,
                                'data': {'description': '', 'items': [{'ref': reads_ref_path}]}})
        # Let's check that we can list set and see reads object as set item
        type_filter = "KBaseSets.ReadsSet"
        ret = self.getImpl().list_objects_with_sets(self.getContext2(),
                                                    {"ws_name": ws_name2,
                                                     "types": [type_filter]})[0]["data"]
        self.assertEqual(1, len(ret))
        item = ret[0]
        self.assertTrue('set_items' in item)
        self.assertTrue('set_items_info' in item['set_items'])
        self.assertEqual(1, len(item['set_items']['set_items_info']))
        # Check access to reads objects
        info = self.getWsClient2().get_object_info_new({'objects': [{'ref': reads_ref_path}]})[0]
        self.assertEqual(reads_obj_name, info[1])

    # @unittest.skip
    # def test_two_users_set_inside_dp(self):
    #     ws_name1_1 = self.createWs()
    #     # Injecting reads object (real copy) into workspace1
    #     orig_reads_obj_ref = self.__class__.example_reads_ref
    #     reads_obj_name = "TestReads"
    #     self.getWsClient().copy_object({'from': {'ref': orig_reads_obj_ref},
    #                                     'to': {'workspace': ws_name1_1,
    #                                            'name': reads_obj_name}})
    #     copy_reads_obj_ref = ws_name1_1 + '/' + reads_obj_name
    #     ws_name1_2 = self.createWs()
    #     set_obj_name = "MyReadsSet.1"
    #     sapi = SetAPI(self.__class__.serviceWizardURL, token=self.getContext()['token'],
    #                   service_ver=self.__class__.SetAPI_version)
    #     sapi.save_reads_set_v1({'workspace': ws_name1_2, 'output_object_name': set_obj_name,
    #                             'data': {'description': '', 'items': [{'ref': copy_reads_obj_ref}]}})
    #     orig_set_ref = ws_name1_2 + '/' + set_obj_name
    #     # Making DP-copy of reads set object by user2
    #     ws_name2 = self.createWs2()
    #     # Let's share workspace containing set with user2
    #     self.getWsClient().set_permissions({'workspace': ws_name1_2, 'new_permission': 'r',
    #                                         'users': [self.getContext2()['user_id']]})
    #     # Import reads set ref into DataPalette of third workspace
    #     dps = DataPaletteService(self.__class__.serviceWizardURL,
    #                               token=self.getContext2()['token'],
    #                               service_ver=self.__class__.DataPalette_version)
    #     dps.add_to_palette({'workspace': ws_name2, 'new_refs': [{'ref': orig_set_ref}]})
    #     dp_ref_map = dps.list_data({'workspaces': [ws_name2]})['data_palette_refs']
    #     set_ref_path = next(iter(dp_ref_map.values())) + ';' + orig_set_ref
    #     reads_ref_path = set_ref_path + ';' + copy_reads_obj_ref
    #     # Un-share original workspace
    #     self.getWsClient().set_permissions({'workspace': ws_name1_2, 'new_permission': 'n',
    #                                         'users': [self.getContext2()['user_id']]})
    #     # Let's check that we can list set and see reads object as set item
    #     ret = self.getImpl().list_objects_with_sets(self.getContext2(),
    #                                                 {"ws_name": ws_name2})[0]["data"]
    #     self.assertEqual(1, len(ret))
    #     item = ret[0]
    #     self.assertTrue('set_items' in item)
    #     self.assertTrue('set_items_info' in item['set_items'])
    #     self.assertEqual(1, len(item['set_items']['set_items_info']))
    #     # Check access to reads and to set objects
    #     info = self.getWsClient2().get_object_info_new({'objects': [{'ref': set_ref_path}]})[0]
    #     self.assertEqual(set_obj_name, info[1])
    #     info = self.getWsClient2().get_object_info_new({'objects': [{'ref': reads_ref_path}]})[0]
    #     self.assertEqual(reads_obj_name, info[1])

    # @unittest.skip
    def test_bulk_list(self):
        try:
            ids = []
            for ws_info in self.getWsClient().list_workspace_info({'perm': 'r', 'excludeGlobal': 1}):
                #ws_name_parts = ws_info[1].split(':')
                #if len(ws_name_parts) == 2 and ws_name_parts[1].isdigit():
                #    continue
                if ws_info[4] < 1000:
                    ids.append(str(ws_info[0]))
                    if len(ids) >= 100:
                        break
            print(("Workspaces selected for bulk list_objects_with_sets: " + str(len(ids))))
            if len(ids) > 0:
                self.getImpl().list_objects_with_sets(self.getContext(), {'workspaces': [ids[0]]})
            NarrativeManager.DEBUG = False  #True
            t1 = time.time()
            ret = self.getImpl().list_objects_with_sets(self.getContext(), {'workspaces': ids})[0]["data"]
            print(("Objects found: " + str(len(ret)) + ", time=" + str(time.time() - t1)))
        finally:
            NarrativeManager.DEBUG = False

    # @unittest.skip
    def test_narratorials(self):
        ws = self.getWsClient()
        ret = self.getImpl().create_new_narrative(self.getContext(),
                                                  {"method": "AssemblyUtil/import_assembly_fasta_ftp",
                                                   "appparam": "0,param1,value1;0,param2,value2",
                                                   "copydata": ""})[0]
        try:
            self.assertTrue('narrativeInfo' in ret)
            wsid = ret['workspaceInfo']['id']

            # 1) make sure new narrative is not in the narratorial list
            nar_list = self.getImpl().list_narratorials(self.getContext(), {})[0]['narratorials']
            self.assertTrue(not in_list(wsid, nar_list))

            # 2) add it, and make sure it is
            self.getImpl().set_narratorial(self.getContext(), {'ws': str(wsid), 'description': 'something'})
            nar_list = self.getImpl().list_narratorials(self.getContext(), {})[0]['narratorials']
            self.assertTrue(in_list(wsid, nar_list))

            # 3) remove it and make sure it goes away
            self.getImpl().remove_narratorial(self.getContext(), {'ws': str(wsid)})
            nar_list = self.getImpl().list_narratorials(self.getContext(), {})[0]['narratorials']
            self.assertTrue(not in_list(wsid, nar_list))

        finally:
            new_ws_id = ret['workspaceInfo']['id']
            ws.delete_workspace({'id': new_ws_id})

    # @unittest.skip
    def test_list_narratives(self):
        ws = self.getWsClient()
        ret = self.getImpl().create_new_narrative(self.getContext(),
                                                  {"method": "",
                                                   "appparam": "",
                                                   "copydata": ""})[0]
        try:
            self.assertTrue('narrativeInfo' in ret)
            wsid = ret['workspaceInfo']['id']
            nar_list = self.getImpl().list_narratives(self.getContext(), {'type': 'mine'})[0]['narratives']
            self.assertTrue(in_list(wsid, nar_list))
            nar_list = self.getImpl().list_narratives(self.getContext(), {'type': 'shared'})[0]['narratives']
            self.assertTrue(not in_list(wsid, nar_list))
            nar_list = self.getImpl().list_narratives(self.getContext(), {'type': 'public'})[0]['narratives']
            self.assertTrue(not in_list(wsid, nar_list))

            # check from User2 perspective, should not be able to see it
            nar_list = self.getImpl().list_narratives(self.getContext2(), {'type': 'mine'})[0]['narratives']
            self.assertTrue(not in_list(wsid, nar_list))
            nar_list = self.getImpl().list_narratives(self.getContext2(), {'type': 'shared'})[0]['narratives']
            self.assertTrue(not in_list(wsid, nar_list))
            nar_list = self.getImpl().list_narratives(self.getContext2(), {'type': 'public'})[0]['narratives']
            self.assertTrue(not in_list(wsid, nar_list))

            # make it public, it should appear in the public list, but not in the shared with me list
            ws.set_global_permission({'id': wsid, 'new_permission': 'r'})
            nar_list = self.getImpl().list_narratives(self.getContext2(), {'type': 'mine'})[0]['narratives']
            self.assertTrue(not in_list(wsid, nar_list))
            nar_list = self.getImpl().list_narratives(self.getContext2(), {'type': 'shared'})[0]['narratives']
            self.assertTrue(not in_list(wsid, nar_list))
            nar_list = self.getImpl().list_narratives(self.getContext2(), {'type': 'public'})[0]['narratives']
            self.assertTrue(in_list(wsid, nar_list))


            # give user2 write access, which should make it visible to user2's shared narrative list
            ws.set_permissions({'id': wsid, 'users': [self.getContext2()['user_id']], 'new_permission': 'r'})
            nar_list = self.getImpl().list_narratives(self.getContext2(), {'type': 'mine'})[0]['narratives']
            self.assertTrue(not in_list(wsid, nar_list))
            nar_list = self.getImpl().list_narratives(self.getContext2(), {'type': 'shared'})[0]['narratives']
            self.assertTrue(in_list(wsid, nar_list))
            nar_list = self.getImpl().list_narratives(self.getContext2(), {'type': 'public'})[0]['narratives']
            self.assertTrue(in_list(wsid, nar_list))

        finally:
            new_ws_id = ret['workspaceInfo']['id']
            ws.delete_workspace({'id': new_ws_id})

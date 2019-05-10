import json
import os
import time
import uuid

from NarrativeService.DataPaletteTypes import DataPaletteTypes
from NarrativeService.ServiceUtils import ServiceUtils
from NarrativeService.WorkspaceListObjectsIterator import WorkspaceListObjectsIterator
from installed_clients.NarrativeMethodStoreClient import NarrativeMethodStore
from installed_clients.WorkspaceClient import Workspace


class NarrativeManager:

    KB_CELL = 'kb-cell'
    KB_TYPE = 'type'
    KB_APP_CELL = 'kb_app'
    KB_FUNCTION_CELL = 'function_input'
    KB_OUTPUT_CELL = 'function_output'
    KB_ERROR_CELL = 'kb_error'
    KB_CODE_CELL = 'kb_code'
    KB_STATE = 'widget_state'

    DEBUG = False

    DATA_PALETTES_TYPES = DataPaletteTypes(False)

    def __init__(self, config, ctx, set_api_cache, dps_cache):
        self.narrativeMethodStoreURL = config['narrative-method-store']
        self.set_api_cache = set_api_cache  # DynamicServiceCache type
        self.dps_cache = dps_cache          # DynamicServiceCache type
        self.token = ctx["token"]
        self.user_id = ctx["user_id"]
        self.ws = Workspace(config['workspace-url'], token=self.token)
        self.intro_md_file = config['intro-markdown-file']
        # We switch DPs on only for internal Continuous Integration environment for now:
        if config['kbase-endpoint'].startswith("https://ci.kbase.us/") or \
           'USE_DP' in os.environ:
                self.DATA_PALETTES_TYPES = DataPaletteTypes(True)

    def list_objects_with_sets(self, ws_id=None, ws_name=None, workspaces=None,
                               types=None, include_metadata=0, include_data_palettes=0):
        if not workspaces:
            if not ws_id and not ws_name:
                raise ValueError("One and only one of 'ws_id', 'ws_name', 'workspaces' " +
                                 "parameters should be set")
            workspaces = [self._get_workspace_name_or_id(ws_id, ws_name)]
        return self._list_objects_with_sets(workspaces, types, include_metadata, include_data_palettes)

    def _list_objects_with_sets(self, workspaces, types, include_metadata, include_data_palettes):
        type_map = None
        if types is not None:
            type_map = {key: True for key in types}

        processed_refs = {}
        data = []
        if self.DEBUG:
            print("NarrativeManager._list_objects_with_sets: processing sets")
        t1 = time.time()
        set_ret = self.set_api_cache.call_method("list_sets",
                                                 [{'workspaces': workspaces,
                                                   'include_set_item_info': 1,
                                                   'include_raw_data_palettes': 1,
                                                   'include_metadata': include_metadata}],
                                                 self.token)
        sets = set_ret['sets']
        dp_data = set_ret.get('raw_data_palettes')
        dp_refs = set_ret.get('raw_data_palette_refs')
        for set_info in sets:
            # Process
            target_set_items = []
            for set_item in set_info['items']:
                target_set_items.append(set_item['info'])
            if self._check_info_type(set_info['info'], type_map):
                data_item = {'object_info': set_info['info'],
                             'set_items': {'set_items_info': target_set_items}}
                data.append(data_item)
                processed_refs[set_info['ref']] = data_item
        if self.DEBUG:
            print("    (time=" + str(time.time() - t1) + ")")

        if self.DEBUG:
            print("NarrativeManager._list_objects_with_sets: loading ws_info")
        t2 = time.time()
        ws_info_list = []
        # for ws in workspaces:
        if len(workspaces) == 1:
            ws = workspaces[0]
            ws_id = None
            ws_name = None
            if str(ws).isdigit():
                ws_id = int(ws)
            else:
                ws_name = str(ws)
            ws_info_list.append(self.ws.get_workspace_info({"id": ws_id, "workspace": ws_name}))
        else:
            ws_map = {key: True for key in workspaces}
            for ws_info in self.ws.list_workspace_info({'perm': 'r'}):
                if ws_info[1] in ws_map or str(ws_info[0]) in ws_map:
                    ws_info_list.append(ws_info)
        if self.DEBUG:
            print("    (time=" + str(time.time() - t2) + ")")

        if self.DEBUG:
            print("NarrativeManager._list_objects_with_sets: loading workspace objects")
        t3 = time.time()
        for info in WorkspaceListObjectsIterator(self.ws,
                                                 ws_info_list=ws_info_list,
                                                 list_objects_params={
                                                     'includeMetadata': include_metadata
                                                 }):
            item_ref = str(info[6]) + '/' + str(info[0]) + '/' + str(info[4])
            if item_ref not in processed_refs and self._check_info_type(info, type_map):
                data_item = {'object_info': info}
                data.append(data_item)
                processed_refs[item_ref] = data_item
        if self.DEBUG:
            print("    (time=" + str(time.time() - t3) + ")")

        return_data = {
            "data": data
        }

        if include_data_palettes == 1:
            if self.DEBUG:
                print("NarrativeManager._list_objects_with_sets: processing DataPalettes")
            t5 = time.time()
            if dp_data is None or dp_refs is None:
                dps = self.dps_cache
                dp_ret = dps.call_method("list_data", [{'workspaces': workspaces,
                                                        'include_metadata': include_metadata}],
                                         self.token)
                dp_data = dp_ret['data']
                dp_refs = dp_ret['data_palette_refs']
            for item in dp_data:
                ref = item['ref']
                if self._check_info_type(item['info'], type_map):
                    data_item = None
                    if ref in processed_refs:
                        data_item = processed_refs[ref]
                    else:
                        data_item = {'object_info': item['info']}
                        processed_refs[ref] = data_item
                        data.append(data_item)
                    dp_info = {}
                    if 'dp_ref' in item:
                        dp_info['ref'] = item['dp_ref']
                    if 'dp_refs' in item:
                        dp_info['refs'] = item['dp_refs']
                    data_item['dp_info'] = dp_info
            return_data["data_palette_refs"] = dp_refs
            if self.DEBUG:
                print("    (time=" + str(time.time() - t5) + ")")

        return return_data

    def _check_info_type(self, info, type_map):
        if type_map is None:
            return True
        obj_type = info[2].split('-')[0]
        return type_map.get(obj_type, False)

    def copy_narrative(self, new_name, narrative_ref):
        """
        Makes a copy of a narrative.
        new_name - new name for the Narrative (user-facing, not object name)
        narrative_ref - object reference for the Narrative to copy
                        (ws/obj/ver, or ws/obj or ws_name/obj_name, etc.)

        This works in the following steps:
        1. Fetch the Narrative object from the Workspace
        2. Clone the Workspace, EXCEPT for the Narrative (maintains ws object ids, versions, etc.)
        3. Save the Narrative object separately so it's at version 1, with updated metadata.
        """
        time_ms = int(round(time.time() * 1000))
        new_ws_name = self.user_id + ':narrative_' + str(time_ms)
        # add the 'narrative' field to newWsMeta later.
        new_ws_meta = {
            "narrative_nice_name": new_name,
            "searchtags": "narrative"
        }

        # Start with getting the existing narrative object, and workspace id
        # from its info (we need the object anyway, and this is cheaper than
        # parsing)
        cur_narrative = self.ws.get_objects([{'ref': narrative_ref}])[0]
        ws_id = cur_narrative['info'][6]

        # Prepare exceptions for cloning the workspace.
        # 1) currentNarrative object:
        excluded_list = [{'objid': cur_narrative['info'][0]}]

        # NO MAS DATA_PALETTES
        # 2) let's exclude objects of types under DataPalette handling:
        # data_palette_type = "DataPalette.DataPalette"
        # excluded_types = [data_palette_type]
        # excluded_types.extend(self.DATA_PALETTES_TYPES.keys())
        # add_to_palette_list = []
        # dp_detected = False
        # for obj_type in excluded_types:
        #     list_objects_params = {'type': obj_type}
        #     if obj_type == data_palette_type:
        #         list_objects_params['showHidden'] = 1
        #     for info in WorkspaceListObjectsIterator(self.ws, ws_id=workspaceId,
        #                                              list_objects_params=list_objects_params):
        #         if obj_type == data_palette_type:
        #             dp_detected = True
        #         else:
        #             add_to_palette_list.append({'ref': str(info[6]) + '/' + str(info[0]) +
        #                                         '/' + str(info[4])})
        #         excluded_list.append({'objid': info[0]})
        # clone the workspace EXCEPT for currentNarrative object + obejcts of DataPalette types:
        new_ws_id = self.ws.clone_workspace({
            'wsi': {'id': ws_id},
            'workspace': new_ws_name,
            'meta': new_ws_meta,
            'exclude': excluded_list
        })[0]
        try:
            # if dp_detected:
            #     self.dps_cache.call_method("copy_palette", [{'from_workspace': str(workspaceId),
            #                                                  'to_workspace': str(newWsId)}],
            #                                self.token)
            # if len(add_to_palette_list) > 0:
            #     # There are objects in source workspace that have type under DataPalette handling
            #     # but these objects are physically stored in source workspace rather that saved
            #     # in DataPalette object. So they weren't copied by "dps.copy_palette".
            #     self.dps_cache.call_method("add_to_palette", [{'workspace': str(newWsId),
            #                                                    'new_refs': add_to_palette_list}],
            #                                self.token)

            # update the ref inside the narrative object and the new workspace metadata.
            new_nar_metadata = cur_narrative['info'][10]
            new_nar_metadata['name'] = new_name
            new_nar_metadata['ws_name'] = new_ws_name
            new_nar_metadata['job_info'] = json.dumps({'queue_time': 0, 'running': 0,
                                                       'completed': 0, 'run_time': 0,
                                                       'error': 0})

            # Set the "is_temporary" metadata flag. This is a string, either "true" or "false"
            # If it's not already present in the old object metadata, it should be set with
            # these rules
            # - true if the name is either "Untitled" or not present,
            # - false otherwise
            is_temporary = new_nar_metadata.get('is_temporary', 'false')
            if 'is_temporary' not in new_nar_metadata:
                if new_nar_metadata.get('name', 'Untitled') == 'Untitled':
                    is_temporary = 'true'
                new_nar_metadata['is_temporary'] = is_temporary

            cur_narrative['data']['metadata']['name'] = new_name
            cur_narrative['data']['metadata']['ws_name'] = new_ws_name
            cur_narrative['data']['metadata']['job_ids'] = {
                'apps': [],
                'methods': [],
                'job_usage': {
                    'queue_time': 0,
                    'run_time': 0
                }
            }
            # save the shiny new Narrative so it's at version 1
            new_nar_info = self.ws.save_objects({
                'id': new_ws_id,
                'objects': [{
                    'type': cur_narrative['info'][2],
                    'data': cur_narrative['data'],
                    'provenance': cur_narrative['provenance'],
                    'name': cur_narrative['info'][1],
                    'meta': new_nar_metadata
                }]
            })
            # now, just update the workspace metadata to point
            # to the new narrative object

            if 'worksheets' in cur_narrative['data']:  # handle legacy.
                num_cells = len(cur_narrative['data']['worksheets'][0]['cells'])
            else:
                num_cells = len(cur_narrative['data']['cells'])
            new_nar_id = new_nar_info[0][0]
            self.ws.alter_workspace_metadata({
                'wsi': {
                    'id': new_ws_id
                },
                'new': {
                    'narrative': str(new_nar_id),
                    'is_temporary': is_temporary,
                    'cell_count': str(num_cells)
                }
            })
            return {'newWsId': new_ws_id, 'newNarId': new_nar_id}
        except Exception:
            # delete copy of workspace so it's out of the way - it's broken
            self.ws.delete_workspace({'id': new_ws_id})
            raise

    def create_new_narrative(self, app, method, appparam, appData, markdown,
                             copydata, importData, includeIntroCell, title):
        if app and method:
            raise ValueError("Must provide no more than one of the app or method params")

        if (not importData) and copydata:
            importData = copydata.split(';')

        if (not appData) and appparam:
            appData = []
            for tmp_item in appparam.split(';'):
                tmp_tuple = tmp_item.split(',')
                step_pos = None
                if tmp_tuple[0]:
                    try:
                        step_pos = int(tmp_tuple[0])
                    except ValueError:
                        pass
                appData.append([step_pos, tmp_tuple[1], tmp_tuple[2]])
        cells = None
        if app:
            cells = [{"app": app}]
        elif method:
            cells = [{"method": method}]
        elif markdown:
            cells = [{"markdown": markdown}]
        narr_info = self._create_temp_narrative(cells, appData, importData, includeIntroCell, title)
        if title is not None:
            # update workspace info so it's not temporary
            pass
        return narr_info

    def _get_intro_markdown(self):
        """
        Creates and returns a cell with the introductory text included.
        """
        # Load introductory markdown text
        with open(self.intro_md_file) as intro_file:
            intro_md = intro_file.read()
        return intro_md

    def _create_temp_narrative(self, cells, parameters, importData, includeIntroCell, title):
        # Migration to python of JavaScript class from https://github.com/kbase/kbase-ui/blob/4d31151d13de0278765a69b2b09f3bcf0e832409/src/client/modules/plugins/narrativemanager/modules/narrativeManager.js#L414
        narr_id = int(round(time.time() * 1000))
        workspaceName = self.user_id + ':narrative_' + str(narr_id)
        narrativeName = "Narrative." + str(narr_id)

        ws = self.ws
        ws_info = ws.create_workspace({'workspace': workspaceName, 'description': ''})
        [narrativeObject, metadataExternal] = self._fetchNarrativeObjects(
            workspaceName, cells, parameters, includeIntroCell, title
        )
        is_temporary = 'true'
        if title is not None and title != 'Untitled':
            is_temporary = 'false'

        metadataExternal['is_temporary'] = is_temporary
        objectInfo = ws.save_objects({'workspace': workspaceName,
                                      'objects': [{'type': 'KBaseNarrative.Narrative',
                                                   'data': narrativeObject,
                                                   'name': narrativeName,
                                                   'meta': metadataExternal,
                                                   'provenance': [{'script': 'NarrativeManager.py',
                                                                   'description': 'Created new ' +
                                                                   'Workspace/Narrative bundle.'}],
                                                   'hidden': 0}]})[0]
        objectInfo = ServiceUtils.object_info_to_object(objectInfo)
        ws_info = self._completeNewNarrative(ws_info[0], objectInfo['id'],
                                             importData, is_temporary, title,
                                             len(narrativeObject['cells']))
        return {
            'workspaceInfo': ServiceUtils.workspace_info_to_object(ws_info),
            'narrativeInfo': objectInfo
        }

    def _fetchNarrativeObjects(self, workspaceName, cells, parameters, includeIntroCell, title):
        if not cells:
            cells = []
        if not title:
            title = 'Untitled'

        # fetchSpecs
        appSpecIds = []
        methodSpecIds = []
        specMapping = {'apps': {}, 'methods': {}}
        for cell in cells:
            if 'app' in cell:
                appSpecIds.append(cell['app'])
            elif 'method' in cell:
                methodSpecIds.append(cell['method'])
        nms = NarrativeMethodStore(self.narrativeMethodStoreURL, token=self.token)
        if len(appSpecIds) > 0:
            appSpecs = nms.get_app_spec({'ids': appSpecIds})
            for spec in appSpecs:
                spec_id = spec['info']['id']
                specMapping['apps'][spec_id] = spec
        if len(methodSpecIds) > 0:
            methodSpecs = nms.get_method_spec({'ids': methodSpecIds})
            for spec in methodSpecs:
                spec_id = spec['info']['id']
                specMapping['methods'][spec_id] = spec
        # end of fetchSpecs

        metadata = {'job_ids': {'methods': [],
                                'apps': [],
                                'job_usage': {'queue_time': 0, 'run_time': 0}},
                    'format': 'ipynb',
                    'creator': self.user_id,
                    'ws_name': workspaceName,
                    'name': title,
                    'type': 'KBaseNarrative.Narrative',
                    'description': '',
                    'data_dependencies': []}
        cellData = self._gatherCellData(cells, specMapping, parameters, includeIntroCell)
        narrativeObject = {'nbformat_minor': 0,
                           'cells': cellData,
                           'metadata': metadata,
                           'nbformat': 4}
        metadataExternal = {}
        for key in metadata:
            value = metadata[key]
            if isinstance(value, str):
                metadataExternal[key] = value
            else:
                metadataExternal[key] = json.dumps(value)
        return [narrativeObject, metadataExternal]

    def _gatherCellData(self, cells, specMapping, parameters, includeIntroCell):
        cell_data = []
        if includeIntroCell == 1:
            cell_data.append({
                'cell_type': 'markdown',
                'source': self._get_intro_markdown(),
                'metadata': {}
            })
        for cell_pos, cell in enumerate(cells):
            if 'app' in cell:
                cell_data.append(self._buildAppCell(len(cell_data),
                                                    specMapping['apps'][cell['app']],
                                                    parameters))
            elif 'method' in cell:
                cell_data.append(self._buildMethodCell(len(cell_data),
                                                       specMapping['methods'][cell['method']],
                                                       parameters))
            elif 'markdown' in cell:
                cell_data.append({'cell_type': 'markdown', 'source': cell['markdown'],
                                  'metadata': {}})
            else:
                raise ValueError("cannot add cell #" + str(cell_pos) +
                                 ", unrecognized cell content")
        return cell_data

    def _buildAppCell(self, pos, spec, params):
        cellId = 'kb-cell-' + str(pos) + '-' + str(uuid.uuid4())
        cell = {
            "cell_type": "markdown",
            "source": "<div id='" + cellId + "'></div>" +
                      "\n<script>" +
                      "$('#" + cellId + "').kbaseNarrativeAppCell({'appSpec' : '" +
                      self._safeJSONStringify(spec) + "', 'cellId' : '" + cellId + "'});" +
                      "</script>",
            "metadata": {}
        }
        cellInfo = {}
        widgetState = []
        cellInfo[self.KB_TYPE] = self.KB_APP_CELL
        cellInfo['app'] = spec
        if params:
            steps = {}
            for param in params:
                stepid = 'step_' + str(param[0])
                if stepid not in steps:
                    steps[stepid] = {}
                    steps[stepid]['inputState'] = {}
                steps[stepid]['inputState'][param[1]] = param[2]
            state = {'state': {'step': steps}}
            widgetState.append(state)
        cellInfo[self.KB_STATE] = widgetState
        cell['metadata'][self.KB_CELL] = cellInfo
        return cell

    def _buildMethodCell(self, pos, spec, params):
        cellId = "kb-cell-" + str(pos) + "-" + str(uuid.uuid4())
        cell = {"cell_type": "markdown",
                "source": "<div id='" + cellId + "'></div>" +
                          "\n<script>" +
                          "$('#" + cellId + "').kbaseNarrativeMethodCell({'method' : '" +
                          self._safeJSONStringify(spec) + "'});" +
                          "</script>",
                "metadata": {}}
        cellInfo = {"method": spec,
                    "widget": spec["widgets"]["input"]}
        cellInfo[self.KB_TYPE] = self.KB_FUNCTION_CELL
        widgetState = []
        if params:
            wparams = {}
            for param in params:
                wparams[param[1]] = param[2]
            widgetState.append({"state": wparams})
        cellInfo[self.KB_STATE] = widgetState
        cell["metadata"][self.KB_CELL] = cellInfo
        return cell

    def _completeNewNarrative(self, workspaceId, objectId, importData, is_temporary, title, num_cells):
        """
        'Completes' the new narrative by updating workspace metadata with the required fields and
        copying in data from the importData list of references.
        """
        new_meta = {
            'narrative': str(objectId),
            'is_temporary': is_temporary,
            'searchtags': 'narrative',
            'cell_count': str(num_cells)
        }
        if is_temporary == 'false' and title is not None:
            new_meta['narrative_nice_name'] = title

        self.ws.alter_workspace_metadata({'wsi': {'id': workspaceId},
                                          'new': new_meta})
        # copy_to_narrative:
        if importData:
            objectsToCopy = [{'ref': x} for x in importData]
            infoList = self.ws.get_object_info_new({'objects': objectsToCopy, 'includeMetadata': 0})
            for item in infoList:
                objectInfo = ServiceUtils.object_info_to_object(item)
                self.copy_object(objectInfo['ref'], workspaceId, None, None, objectInfo)

        return self.ws.get_workspace_info({'id': workspaceId})

    def _safeJSONStringify(self, obj):
        return json.dumps(self._safeJSONStringifyPrepare(obj))

    def _safeJSONStringifyPrepare(self, obj):
        if isinstance(obj, str):
            return obj.replace("'", "&apos;").replace('"', "&quot;")
        elif isinstance(obj, list):
            for pos in range(len(obj)):
                obj[pos] = self._safeJSONStringifyPrepare(obj[pos])
        elif isinstance(obj, dict):
            obj_keys = list(obj.keys())
            for key in obj_keys:
                obj[key] = self._safeJSONStringifyPrepare(obj[key])
        else:
            pass  # it's boolean/int/float/None
        return obj

    def _get_workspace_name_or_id(self, ws_id, ws_name):
        ret = ws_name
        if not ret:
            ret = str(ws_id)
        return ret

    def copy_object(self, ref, target_ws_id, target_ws_name, target_name, src_info):
        """
        Copies an object from one workspace to another.
        """
        if not target_ws_id and not target_ws_name:
            raise ValueError("Neither target workspace id nor name is defined")
        if not src_info:
            src_info_tuple = self.ws.get_object_info_new({'objects': [{'ref': ref}],
                                                          'includeMetadata': 0})[0]
            src_info = ServiceUtils.object_info_to_object(src_info_tuple)
        if not target_name:
            target_name = src_info['name']
        obj_info_tuple = self.ws.copy_object({
            'from': {'ref': ref},
            'to': {
                'wsid': target_ws_id,
                'workspace': target_ws_name,
                'name': target_name
            }
        })
        obj_info = ServiceUtils.object_info_to_object(obj_info_tuple)
        return {'info': obj_info}

    def list_available_types(self, workspaces):
        data = self.list_objects_with_sets(workspaces=workspaces)['data']
        type_stat = {}
        for item in data:
            info = item['object_info']
            obj_type = info[2].split('-')[0]
            if obj_type in type_stat:
                type_stat[obj_type] += 1
            else:
                type_stat[obj_type] = 1
        return {'type_stat': type_stat}

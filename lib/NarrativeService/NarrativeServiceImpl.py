# -*- coding: utf-8 -*-
#BEGIN_HEADER
from NarrativeService.DynamicServiceCache import DynamicServiceClient
from NarrativeService.NarrativeListUtils import NarrativeListUtils, NarratorialUtils
from NarrativeService.NarrativeManager import NarrativeManager
from NarrativeService.ReportFetcher import ReportFetcher
from NarrativeService.sharing.sharemanager import ShareRequester
from NarrativeService.apps.appinfo import get_all_app_info, get_ignore_categories
from installed_clients.WorkspaceClient import Workspace
#END_HEADER


class NarrativeService:
    '''
    Module Name:
    NarrativeService

    Module Description:
    A KBase module: NarrativeService
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.2.1"
    GIT_URL = "https://github.com/briehl/NarrativeService"
    GIT_COMMIT_HASH = "d57f119e95cc9b8132ff4993cb0de4e11a0eb3ff"

    #BEGIN_CLASS_HEADER
    def _nm(self, ctx):
        """
        ctx - the context object, gets tokens, etc.
        """
        return NarrativeManager(self.config, ctx, self.setAPIClient, self.dataPaletteClient)
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.config = config
        self.workspaceURL = config['workspace-url']
        self.serviceWizardURL = config['service-wizard']
        self.narrativeMethodStoreURL = config['narrative-method-store']
        self.catalogURL = config['catalog-url']
        self.setAPIClient = DynamicServiceClient(self.serviceWizardURL,
                                                 config['setapi-version'],
                                                 'SetAPI')
        self.dataPaletteClient = DynamicServiceClient(self.serviceWizardURL,
                                                      config['datapaletteservice-version'],
                                                      'DataPaletteService')

        self.narListUtils = NarrativeListUtils(config['narrative-list-cache-size'])
        #END_CONSTRUCTOR
        pass


    def list_objects_with_sets(self, ctx, params):
        """
        :param params: instance of type "ListObjectsWithSetsParams"
           (ws_name/ws_id/workspaces - alternative way of defining workspaces
           (in case of 'workspaces' each string could be workspace name or ID
           converted into string). types - optional filter field, limiting
           output list to set of types. includeMetadata - if 1, includes
           object metadata, if 0, does not. Default 0. include_data_palettes
           - if 1, includes data palette info, if 0, does not. Default 0.) ->
           structure: parameter "ws_name" of String, parameter "ws_id" of
           Long, parameter "workspaces" of list of String, parameter "types"
           of list of String, parameter "includeMetadata" of type "boolean"
           (@range [0,1]), parameter "include_data_palettes" of type
           "boolean" (@range [0,1])
        :returns: instance of type "ListObjectsWithSetsOutput"
           (data_palette_refs - mapping from workspace Id to reference to
           DataPalette container existing in given workspace. Not present if
           include_data_palettes is 0 in the input parameters.) -> structure:
           parameter "data" of list of type "ListItem" (object_info -
           workspace info for object (including set object), set_items -
           optional property listing info for items of set object, dp_info -
           optional data-palette info (defined for items stored in
           DataPalette object).) -> structure: parameter "object_info" of
           type "object_info" (Information about an object, including user
           provided metadata. obj_id objid - the numerical id of the object.
           obj_name name - the name of the object. type_string type - the
           type of the object. timestamp save_date - the save date of the
           object. obj_ver ver - the version of the object. username saved_by
           - the user that saved or copied the object. ws_id wsid - the
           workspace containing the object. ws_name workspace - the workspace
           containing the object. string chsum - the md5 checksum of the
           object. int size - the size of the object in bytes. usermeta meta
           - arbitrary user-supplied metadata about the object.) -> tuple of
           size 11: parameter "objid" of Long, parameter "name" of String,
           parameter "type" of String, parameter "save_date" of type
           "timestamp" (A time in the format YYYY-MM-DDThh:mm:ssZ, where Z is
           either the character Z (representing the UTC timezone) or the
           difference in time to UTC in the format +/-HHMM, eg:
           2012-12-17T23:24:06-0500 (EST time) 2013-04-03T08:56:32+0000 (UTC
           time) 2013-04-03T08:56:32Z (UTC time)), parameter "version" of
           Long, parameter "saved_by" of String, parameter "wsid" of Long,
           parameter "workspace" of String, parameter "chsum" of String,
           parameter "size" of Long, parameter "meta" of mapping from String
           to String, parameter "set_items" of type "SetItems" -> structure:
           parameter "set_items_info" of list of type "object_info"
           (Information about an object, including user provided metadata.
           obj_id objid - the numerical id of the object. obj_name name - the
           name of the object. type_string type - the type of the object.
           timestamp save_date - the save date of the object. obj_ver ver -
           the version of the object. username saved_by - the user that saved
           or copied the object. ws_id wsid - the workspace containing the
           object. ws_name workspace - the workspace containing the object.
           string chsum - the md5 checksum of the object. int size - the size
           of the object in bytes. usermeta meta - arbitrary user-supplied
           metadata about the object.) -> tuple of size 11: parameter "objid"
           of Long, parameter "name" of String, parameter "type" of String,
           parameter "save_date" of type "timestamp" (A time in the format
           YYYY-MM-DDThh:mm:ssZ, where Z is either the character Z
           (representing the UTC timezone) or the difference in time to UTC
           in the format +/-HHMM, eg: 2012-12-17T23:24:06-0500 (EST time)
           2013-04-03T08:56:32+0000 (UTC time) 2013-04-03T08:56:32Z (UTC
           time)), parameter "version" of Long, parameter "saved_by" of
           String, parameter "wsid" of Long, parameter "workspace" of String,
           parameter "chsum" of String, parameter "size" of Long, parameter
           "meta" of mapping from String to String, parameter "dp_info" of
           type "DataPaletteInfo" (ref - reference to any DataPalette
           container pointing to given object, refs - list of references to
           all DataPalette containers pointing to given object.) ->
           structure: parameter "ref" of String, parameter "refs" of list of
           String, parameter "data_palette_refs" of mapping from String to
           String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN list_objects_with_sets
        ws_id = params.get("ws_id")
        ws_name = params.get("ws_name")
        workspaces = params.get("workspaces")
        types = params.get("types")
        include_metadata = params.get("includeMetadata", 0)
        include_data_palettes = params.get("include_data_palettes", 0)
        returnVal = self._nm(ctx).list_objects_with_sets(
            ws_id=ws_id, ws_name=ws_name, workspaces=workspaces, types=types,
            include_metadata=include_metadata, include_data_palettes=include_data_palettes
        )
        #END list_objects_with_sets

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method list_objects_with_sets return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def copy_narrative(self, ctx, params):
        """
        :param params: instance of type "CopyNarrativeParams" (workspaceId -
           optional workspace ID, if not specified then property from
           workspaceRef object info is used.) -> structure: parameter
           "workspaceRef" of String, parameter "workspaceId" of Long,
           parameter "newName" of String
        :returns: instance of type "CopyNarrativeOutput" -> structure:
           parameter "newWsId" of Long, parameter "newNarId" of Long
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN copy_narrative
        newName = params['newName']
        workspaceRef = params['workspaceRef']
        returnVal = self._nm(ctx).copy_narrative(newName, workspaceRef)
        #END copy_narrative

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method copy_narrative return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def create_new_narrative(self, ctx, params):
        """
        :param params: instance of type "CreateNewNarrativeParams" (app -
           name of app (optional, either app or method may be defined) method
           - name of method (optional, either app or method may be defined)
           appparam - parameters of app/method packed into string in format:
           "step_pos,param_name,param_value(;...)*" (alternative to appData)
           appData - parameters of app/method in unpacked form (alternative
           to appparam) markdown - markdown text for cell of 'markdown' type
           (optional) copydata - packed import data in format "import(;...)*"
           (alternative to importData) importData - import data in unpacked
           form (alternative to copydata) includeIntroCell - if 1, adds an
           introductory markdown cell at the top (optional, default 0) title
           - name of the new narrative (optional, if a string besides
           'Untitled', this will mark the narrative as not temporary, so it
           will appear in the dashboard)) -> structure: parameter "app" of
           String, parameter "method" of String, parameter "appparam" of
           String, parameter "appData" of list of type "AppParam" -> tuple of
           size 3: parameter "step_pos" of Long, parameter "key" of String,
           parameter "value" of String, parameter "markdown" of String,
           parameter "copydata" of String, parameter "importData" of list of
           String, parameter "includeIntroCell" of type "boolean" (@range
           [0,1]), parameter "title" of String
        :returns: instance of type "CreateNewNarrativeOutput" -> structure:
           parameter "workspaceInfo" of type "WorkspaceInfo" (Restructured
           workspace info 'wsInfo' tuple: id: wsInfo[0], name: wsInfo[1],
           owner: wsInfo[2], moddate: wsInfo[3], object_count: wsInfo[4],
           user_permission: wsInfo[5], globalread: wsInfo[6], lockstat:
           wsInfo[7], metadata: wsInfo[8], modDateMs:
           ServiceUtils.iso8601ToMillisSinceEpoch(wsInfo[3])) -> structure:
           parameter "id" of Long, parameter "name" of String, parameter
           "owner" of String, parameter "moddate" of type "timestamp" (A time
           in the format YYYY-MM-DDThh:mm:ssZ, where Z is either the
           character Z (representing the UTC timezone) or the difference in
           time to UTC in the format +/-HHMM, eg: 2012-12-17T23:24:06-0500
           (EST time) 2013-04-03T08:56:32+0000 (UTC time)
           2013-04-03T08:56:32Z (UTC time)), parameter "object_count" of
           Long, parameter "user_permission" of type "permission" (Represents
           the permissions a user or users have to a workspace: 'a' -
           administrator. All operations allowed. 'w' - read/write. 'r' -
           read. 'n' - no permissions.), parameter "globalread" of type
           "permission" (Represents the permissions a user or users have to a
           workspace: 'a' - administrator. All operations allowed. 'w' -
           read/write. 'r' - read. 'n' - no permissions.), parameter
           "lockstat" of type "lock_status" (The lock status of a workspace.
           One of 'unlocked', 'locked', or 'published'.), parameter
           "metadata" of mapping from String to String, parameter "modDateMs"
           of Long, parameter "narrativeInfo" of type "ObjectInfo"
           (Restructured workspace object info 'data' tuple: id: data[0],
           name: data[1], type: data[2], save_date: data[3], version:
           data[4], saved_by: data[5], wsid: data[6], ws: data[7], checksum:
           data[8], size: data[9], metadata: data[10], ref: data[6] + '/' +
           data[0] + '/' + data[4], obj_id: 'ws.' + data[6] + '.obj.' +
           data[0], typeModule: type[0], typeName: type[1], typeMajorVersion:
           type[2], typeMinorVersion: type[3], saveDateMs:
           ServiceUtils.iso8601ToMillisSinceEpoch(data[3])) -> structure:
           parameter "id" of Long, parameter "name" of String, parameter
           "type" of String, parameter "save_date" of String, parameter
           "version" of Long, parameter "saved_by" of String, parameter
           "wsid" of Long, parameter "ws" of String, parameter "checksum" of
           String, parameter "size" of Long, parameter "metadata" of mapping
           from String to String, parameter "ref" of String, parameter
           "obj_id" of String, parameter "typeModule" of String, parameter
           "typeName" of String, parameter "typeMajorVersion" of String,
           parameter "typeMinorVersion" of String, parameter "saveDateMs" of
           Long
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN create_new_narrative
        app = params.get('app')
        method = params.get('method')
        appparam = params.get('appparam')
        appData = params.get('appData')
        markdown = params.get('markdown')
        copydata = params.get('copydata')
        importData = params.get('importData')
        includeIntroCell = params.get('includeIntroCell', 0)
        title = params.get('title', None)
        returnVal = self._nm(ctx).create_new_narrative(
            app, method, appparam, appData, markdown, copydata, importData,
            includeIntroCell, title
        )
        #END create_new_narrative

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method create_new_narrative return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def copy_object(self, ctx, params):
        """
        :param params: instance of type "CopyObjectParams" (ref - workspace
           reference to source object, target_ws_id/target_ws_name -
           alternative ways to define target workspace, target_name -
           optional target object name (if not set then source object name is
           used).) -> structure: parameter "ref" of String, parameter
           "target_ws_id" of Long, parameter "target_ws_name" of String,
           parameter "target_name" of String
        :returns: instance of type "CopyObjectOutput" (info - workspace info
           of created object) -> structure: parameter "info" of type
           "ObjectInfo" (Restructured workspace object info 'data' tuple: id:
           data[0], name: data[1], type: data[2], save_date: data[3],
           version: data[4], saved_by: data[5], wsid: data[6], ws: data[7],
           checksum: data[8], size: data[9], metadata: data[10], ref: data[6]
           + '/' + data[0] + '/' + data[4], obj_id: 'ws.' + data[6] + '.obj.'
           + data[0], typeModule: type[0], typeName: type[1],
           typeMajorVersion: type[2], typeMinorVersion: type[3], saveDateMs:
           ServiceUtils.iso8601ToMillisSinceEpoch(data[3])) -> structure:
           parameter "id" of Long, parameter "name" of String, parameter
           "type" of String, parameter "save_date" of String, parameter
           "version" of Long, parameter "saved_by" of String, parameter
           "wsid" of Long, parameter "ws" of String, parameter "checksum" of
           String, parameter "size" of Long, parameter "metadata" of mapping
           from String to String, parameter "ref" of String, parameter
           "obj_id" of String, parameter "typeModule" of String, parameter
           "typeName" of String, parameter "typeMajorVersion" of String,
           parameter "typeMinorVersion" of String, parameter "saveDateMs" of
           Long
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN copy_object
        ref = params['ref']
        target_ws_id = params.get('target_ws_id')
        target_ws_name = params.get('target_ws_name')
        target_name = params.get('target_name')
        returnVal = self._nm(ctx).copy_object(ref, target_ws_id, target_ws_name, target_name, None)
        #END copy_object

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method copy_object return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def list_available_types(self, ctx, params):
        """
        :param params: instance of type "ListAvailableTypesParams"
           (workspaces - list of items where each one is workspace name of
           textual ID.) -> structure: parameter "workspaces" of list of String
        :returns: instance of type "ListAvailableTypesOutput" (type_stat -
           number of objects by type) -> structure: parameter "type_stat" of
           mapping from String to Long
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN list_available_types
        workspaces = params.get("workspaces")
        returnVal = self._nm(ctx).list_available_types(workspaces)
        #END list_available_types

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method list_available_types return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def list_narratorials(self, ctx, params):
        """
        :param params: instance of type "ListNarratorialParams" (Listing
           Narratives / Naratorials (plus Narratorial Management)) ->
           structure:
        :returns: instance of type "NarratorialList" -> structure: parameter
           "narratorials" of list of type "Narratorial" (info for a
           narratorial) -> structure: parameter "ws" of type "workspace_info"
           (Information about a workspace. ws_id id - the numerical ID of the
           workspace. ws_name workspace - name of the workspace. username
           owner - name of the user who owns (e.g. created) this workspace.
           timestamp moddate - date when the workspace was last modified. int
           max_objid - the maximum object ID appearing in this workspace.
           Since cloning a workspace preserves object IDs, this number may be
           greater than the number of objects in a newly cloned workspace.
           permission user_permission - permissions for the authenticated
           user of this workspace. permission globalread - whether this
           workspace is globally readable. lock_status lockstat - the status
           of the workspace lock. usermeta metadata - arbitrary user-supplied
           metadata about the workspace.) -> tuple of size 9: parameter "id"
           of Long, parameter "workspace" of String, parameter "owner" of
           String, parameter "moddate" of String, parameter "max_objid" of
           Long, parameter "user_permission" of String, parameter
           "globalread" of String, parameter "lockstat" of String, parameter
           "metadata" of mapping from String to String, parameter "nar" of
           type "object_info" (Information about an object, including user
           provided metadata. obj_id objid - the numerical id of the object.
           obj_name name - the name of the object. type_string type - the
           type of the object. timestamp save_date - the save date of the
           object. obj_ver ver - the version of the object. username saved_by
           - the user that saved or copied the object. ws_id wsid - the
           workspace containing the object. ws_name workspace - the workspace
           containing the object. string chsum - the md5 checksum of the
           object. int size - the size of the object in bytes. usermeta meta
           - arbitrary user-supplied metadata about the object.) -> tuple of
           size 11: parameter "objid" of Long, parameter "name" of String,
           parameter "type" of String, parameter "save_date" of type
           "timestamp" (A time in the format YYYY-MM-DDThh:mm:ssZ, where Z is
           either the character Z (representing the UTC timezone) or the
           difference in time to UTC in the format +/-HHMM, eg:
           2012-12-17T23:24:06-0500 (EST time) 2013-04-03T08:56:32+0000 (UTC
           time) 2013-04-03T08:56:32Z (UTC time)), parameter "version" of
           Long, parameter "saved_by" of String, parameter "wsid" of Long,
           parameter "workspace" of String, parameter "chsum" of String,
           parameter "size" of Long, parameter "meta" of mapping from String
           to String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN list_narratorials
        ws = Workspace(self.workspaceURL, token=ctx["token"])
        returnVal = {'narratorials': self.narListUtils.list_narratorials(ws)}
        #END list_narratorials

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method list_narratorials return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def list_narratives(self, ctx, params):
        """
        :param params: instance of type "ListNarrativeParams" (List
           narratives type parameter indicates which narratives to return.
           Supported options are for now 'mine', 'public', or 'shared') ->
           structure: parameter "type" of String
        :returns: instance of type "NarrativeList" -> structure: parameter
           "narratives" of list of type "Narrative" -> structure: parameter
           "ws" of type "workspace_info" (Information about a workspace.
           ws_id id - the numerical ID of the workspace. ws_name workspace -
           name of the workspace. username owner - name of the user who owns
           (e.g. created) this workspace. timestamp moddate - date when the
           workspace was last modified. int max_objid - the maximum object ID
           appearing in this workspace. Since cloning a workspace preserves
           object IDs, this number may be greater than the number of objects
           in a newly cloned workspace. permission user_permission -
           permissions for the authenticated user of this workspace.
           permission globalread - whether this workspace is globally
           readable. lock_status lockstat - the status of the workspace lock.
           usermeta metadata - arbitrary user-supplied metadata about the
           workspace.) -> tuple of size 9: parameter "id" of Long, parameter
           "workspace" of String, parameter "owner" of String, parameter
           "moddate" of String, parameter "max_objid" of Long, parameter
           "user_permission" of String, parameter "globalread" of String,
           parameter "lockstat" of String, parameter "metadata" of mapping
           from String to String, parameter "nar" of type "object_info"
           (Information about an object, including user provided metadata.
           obj_id objid - the numerical id of the object. obj_name name - the
           name of the object. type_string type - the type of the object.
           timestamp save_date - the save date of the object. obj_ver ver -
           the version of the object. username saved_by - the user that saved
           or copied the object. ws_id wsid - the workspace containing the
           object. ws_name workspace - the workspace containing the object.
           string chsum - the md5 checksum of the object. int size - the size
           of the object in bytes. usermeta meta - arbitrary user-supplied
           metadata about the object.) -> tuple of size 11: parameter "objid"
           of Long, parameter "name" of String, parameter "type" of String,
           parameter "save_date" of type "timestamp" (A time in the format
           YYYY-MM-DDThh:mm:ssZ, where Z is either the character Z
           (representing the UTC timezone) or the difference in time to UTC
           in the format +/-HHMM, eg: 2012-12-17T23:24:06-0500 (EST time)
           2013-04-03T08:56:32+0000 (UTC time) 2013-04-03T08:56:32Z (UTC
           time)), parameter "version" of Long, parameter "saved_by" of
           String, parameter "wsid" of Long, parameter "workspace" of String,
           parameter "chsum" of String, parameter "size" of Long, parameter
           "meta" of mapping from String to String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN list_narratives
        ws = Workspace(self.workspaceURL, token=ctx["token"])
        nar_type = 'mine'
        valid_types = ['mine', 'shared', 'public']
        if 'type' in params:
            nar_type = params['type']

        returnVal = {'narratives': []}
        if nar_type == 'mine':
            returnVal['narratives'] = self.narListUtils.list_my_narratives(ctx['user_id'], ws)
        elif nar_type == 'shared':
            returnVal['narratives'] = self.narListUtils.list_shared_narratives(ctx['user_id'], ws)
        elif nar_type == 'public':
            returnVal['narratives'] = self.narListUtils.list_public_narratives(ws)
        else:
            raise ValueError('"type" parameter must be set to one of: ' + str(valid_types))
        #END list_narratives

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method list_narratives return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def set_narratorial(self, ctx, params):
        """
        Allows a user to create a Narratorial given a WS they own. Right now
        anyone can do this, but we may restrict in the future to users that
        have a particular role.  Run simply as:
            ns.set_narratorial({'ws':'MyWsName'}) or,
            ns.set_narratorial({'ws':'4231'})
        :param params: instance of type "SetNarratorialParams" (ws field is a
           string, but properly interpreted whether it is a workspace name or
           ID) -> structure: parameter "ws" of String, parameter
           "description" of String
        :returns: instance of type "SetNarratorialResult" -> structure:
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN set_narratorial
        if 'ws' not in params:
            raise ValueError('"ws" field indicating WS name or id is required.')
        if 'description' not in params:
            raise ValueError('"description" field indicating WS name or id is required.')
        ws = Workspace(self.workspaceURL, token=ctx["token"])
        nu = NarratorialUtils()
        nu.set_narratorial(params['ws'], params['description'], ws)
        returnVal = {}
        #END set_narratorial

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method set_narratorial return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def remove_narratorial(self, ctx, params):
        """
        :param params: instance of type "RemoveNarratorialParams" ->
           structure: parameter "ws" of String
        :returns: instance of type "RemoveNarratorialResult" -> structure:
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN remove_narratorial
        if 'ws' not in params:
            raise ValueError('"ws" field indicating WS name or id is required.')
        ws = Workspace(self.workspaceURL, token=ctx["token"])
        nu = NarratorialUtils()
        nu.remove_narratorial(params['ws'], ws)
        returnVal = {}
        #END remove_narratorial

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method remove_narratorial return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def find_object_report(self, ctx, params):
        """
        find_object_report searches for a referencing report. All reports (if made properly) reference the objects
        that were created at the same time. To find that report, we search back up the reference chain.
        If the object in question was a copy, then there is no referencing report. We might still want to see it,
        though! If the original object is accessible, we'll continue the search from that object, and mark the
        associated object UPA in the return value.
        :param params: instance of type "FindObjectReportParams" (This first
           version only takes a single UPA as input and attempts to find the
           report that made it.) -> structure: parameter "upa" of String
        :returns: instance of type "FindObjectReportOutput" (report_upas: the
           UPAs for the report object. If empty list, then no report is
           available. But there might be more than one... object_upa: the UPA
           for the object that this report references. If the originally
           passed object was copied, then this will be the source of that
           copy that has a referencing report. copy_inaccessible: 1 if this
           object was copied, and the user can't see the source, so no
           report's available. error: if an error occurred while looking up
           (found an unavailable copy, or the report is not accessible), this
           will have a sensible string, more or less. Optional.) ->
           structure: parameter "report_upas" of list of String, parameter
           "object_upa" of String, parameter "copy_inaccessible" of type
           "boolean" (@range [0,1]), parameter "error" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN find_object_report
        report_fetcher = ReportFetcher(Workspace(self.workspaceURL, token=ctx["token"]))
        returnVal = report_fetcher.find_report_from_object(params['upa'])
        #END find_object_report

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method find_object_report return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def request_narrative_share(self, ctx, params):
        """
        This sends a notification to the admins of a workspace (or anyone with share privileges) that a
        user would like access to it.
        If a request has already been made, this will fail and return with the string "a request has already been made"
        :param params: instance of type "RequestNarrativeShareInput" (ws_id:
           The workspace id containing the narrative to share share_level:
           The level of sharing requested - one of "r" (read), "w" (write),
           "a" (admin) user: The user to be shared with) -> structure:
           parameter "ws_id" of Long, parameter "share_level" of String,
           parameter "user" of String
        :returns: instance of type "RequestNarrativeShareOutput" (ok: 0 if
           the request failed, 1 if the request succeeded. error (optional):
           if a failure happened during the request, this has a reason why.
           Not present if it succeeded.) -> structure: parameter "ok" of type
           "boolean" (@range [0,1]), parameter "error" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN request_narrative_share
        sm = ShareRequester(params, self.config)
        returnVal = sm.request_share()
        #END request_narrative_share

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method request_narrative_share return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def get_all_app_info(self, ctx, input):
        """
        This returns all app info from the KBase catalog, formatted in a way to make life easy for the
        Narrative APPS panel on startup.
        :param input: instance of type "GetAppInfoInput" -> structure:
           parameter "tag" of String, parameter "user_id" of String
        :returns: instance of type "AllAppInfo" -> structure: parameter
           "module_versions" of mapping from String to String, parameter
           "categories" of mapping from String to type "CategoryInfo" ->
           structure: parameter "description" of String, parameter "id" of
           String, parameter "name" of String, parameter "parent_ids" of
           String, parameter "tooltip" of String, parameter "ver" of String,
           parameter "app_infos" of mapping from String to mapping from
           String to type "AppInfo" (favorite is optional - if the app is one
           of the user's favorites, this will be the timestamp when it was
           made a favorite.) -> structure: parameter "app_type" of String,
           parameter "authors" of list of String, parameter "categories" of
           list of String, parameter "git_commit_hash" of String, parameter
           "id" of String, parameter "input_types" of list of String,
           parameter "module_name" of String, parameter "name" of String,
           parameter "namespace" of String, parameter "output_types" of list
           of String, parameter "subtitle" of String, parameter "tooltip" of
           String, parameter "ver" of String, parameter "favorite" of Long
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN get_all_app_info
        output = get_all_app_info(input['tag'], input['user'],
                                  self.narrativeMethodStoreURL, self.catalogURL)
        #END get_all_app_info

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method get_all_app_info return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def get_ignore_categories(self, ctx):
        """
        This returns ignored app categories used in Narrative Apps Panel.
        :returns: instance of mapping from String to Long
        """
        # ctx is the context object
        # return variables are: ignore_categories
        #BEGIN get_ignore_categories
        ignore_categories = get_ignore_categories()
        #END get_ignore_categories

        # At some point might do deeper type checking...
        if not isinstance(ignore_categories, dict):
            raise ValueError('Method get_ignore_categories return value ' +
                             'ignore_categories is not type dict as required.')
        # return the results
        return [ignore_categories]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]

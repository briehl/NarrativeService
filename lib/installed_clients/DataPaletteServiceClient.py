# -*- coding: utf-8 -*-
############################################################
#
# Autogenerated by the KBase type compiler -
# any changes made here will be overwritten
#
############################################################

from __future__ import print_function
# the following is a hack to get the baseclient to import whether we're in a
# package or not. This makes pep8 unhappy hence the annotations.
try:
    # baseclient and this client are in a package
    from .baseclient import BaseClient as _BaseClient  # @UnusedImport
except ImportError:
    # no they aren't
    from baseclient import BaseClient as _BaseClient  # @Reimport


class DataPaletteService(object):

    def __init__(
            self, url=None, timeout=30 * 60, user_id=None,
            password=None, token=None, ignore_authrc=False,
            trust_all_ssl_certificates=False,
            auth_svc='https://ci.kbase.us/services/auth/api/legacy/KBase/Sessions/Login',
            service_ver='release',
            async_job_check_time_ms=100, async_job_check_time_scale_percent=150, 
            async_job_check_max_time_ms=300000):
        if url is None:
            raise ValueError('A url is required')
        self._service_ver = service_ver
        self._client = _BaseClient(
            url, timeout=timeout, user_id=user_id, password=password,
            token=token, ignore_authrc=ignore_authrc,
            trust_all_ssl_certificates=trust_all_ssl_certificates,
            auth_svc=auth_svc,
            async_job_check_time_ms=async_job_check_time_ms,
            async_job_check_time_scale_percent=async_job_check_time_scale_percent,
            async_job_check_max_time_ms=async_job_check_max_time_ms)

    def list_data(self, params, context=None):
        """
        :param params: instance of type "ListDataParams" (workspaces - list
           of workspace names or IDs (converted to strings), include_metadata
           - if 1, includes object metadata, if 0, does not. Default 0. TODO:
           pagination?) -> structure: parameter "workspaces" of list of type
           "ws_name_or_id", parameter "include_metadata" of type "boolean"
           (@range [0,1])
        :returns: instance of type "DataList" (data_palette_refs - mapping
           from workspace ID to reference to DataPalette container object.)
           -> structure: parameter "data" of list of type "DataInfo" (dp_ref
           - reference to DataPalette container pointing to given object,
           dp_refs - full list of references to DataPalette containers that
           point to given object (in contrast to dp_ref which shows only
           first item from dp_refs list).) -> structure: parameter "ref" of
           type "ws_ref" (@id ws), parameter "info" of type "object_info"
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
           of type "obj_id" (The unique, permanent numerical ID of an
           object.), parameter "name" of type "obj_name" (A string used as a
           name for an object. Any string consisting of alphanumeric
           characters and the characters |._- that is not an integer is
           acceptable.), parameter "type" of type "type_string" (A type
           string. Specifies the type and its version in a single string in
           the format [module].[typename]-[major].[minor]: module - a string.
           The module name of the typespec containing the type. typename - a
           string. The name of the type as assigned by the typedef statement.
           major - an integer. The major version of the type. A change in the
           major version implies the type has changed in a non-backwards
           compatible way. minor - an integer. The minor version of the type.
           A change in the minor version implies that the type has changed in
           a way that is backwards compatible with previous type definitions.
           In many cases, the major and minor versions are optional, and if
           not provided the most recent version will be used. Example:
           MyModule.MyType-3.1), parameter "save_date" of type "timestamp" (A
           time in the format YYYY-MM-DDThh:mm:ssZ, where Z is either the
           character Z (representing the UTC timezone) or the difference in
           time to UTC in the format +/-HHMM, eg: 2012-12-17T23:24:06-0500
           (EST time) 2013-04-03T08:56:32+0000 (UTC time)
           2013-04-03T08:56:32Z (UTC time)), parameter "version" of Long,
           parameter "saved_by" of type "username" (Login name of a KBase
           user account.), parameter "wsid" of type "ws_id" (The unique,
           permanent numerical ID of a workspace.), parameter "workspace" of
           type "ws_name" (A string used as a name for a workspace. Any
           string consisting of alphanumeric characters and "_", ".", or "-"
           that is not an integer is acceptable. The name may optionally be
           prefixed with the workspace owner's user name and a colon, e.g.
           kbasetest:my_workspace.), parameter "chsum" of String, parameter
           "size" of Long, parameter "meta" of type "usermeta" (User provided
           metadata about an object. Arbitrary key-value pairs provided by
           the user.) -> mapping from String to String, parameter "dp_ref" of
           type "ws_ref" (@id ws), parameter "dp_refs" of list of type
           "ws_ref" (@id ws), parameter "data_palette_refs" of mapping from
           type "ws_text_id" (String with numeric ID of workspace (working as
           key in mapping).) to type "ws_ref" (@id ws)
        """
        return self._client.run_job('DataPaletteService.list_data',
                                    [params], self._service_ver, context)

    def add_to_palette(self, params, context=None):
        """
        :param params: instance of type "AddToPaletteParams" -> structure:
           parameter "workspace" of type "ws_name_or_id", parameter
           "new_refs" of list of type "ObjectReference" (ref - is workspace
           reference or ref-path string) -> structure: parameter "ref" of
           type "ws_ref" (@id ws)
        :returns: instance of type "AddToPaletteResult" -> structure:
        """
        return self._client.run_job('DataPaletteService.add_to_palette',
                                    [params], self._service_ver, context)

    def remove_from_palette(self, params, context=None):
        """
        Note: right now you must provide the exact, absolute reference of the
        item to delete (e.g. 2524/3/1) and matched exactly to be removed.  Relative
        refs will not be matched.  Currently, this method will throw an error
        if a provided reference was not found in the palette.
        :param params: instance of type "RemoveFromPaletteParams" ->
           structure: parameter "workspace" of type "ws_name_or_id",
           parameter "refs" of list of type "ws_ref" (@id ws)
        :returns: instance of type "RemoveFromPaletteResult" -> structure:
        """
        return self._client.run_job('DataPaletteService.remove_from_palette',
                                    [params], self._service_ver, context)

    def copy_palette(self, params, context=None):
        """
        :param params: instance of type "CopyPaletteParams" -> structure:
           parameter "from_workspace" of type "ws_name_or_id", parameter
           "to_workspace" of type "ws_name_or_id"
        :returns: instance of type "CopyPaletteResult" -> structure:
        """
        return self._client.run_job('DataPaletteService.copy_palette',
                                    [params], self._service_ver, context)

    def set_palette_for_ws(self, params, context=None):
        """
        In case the WS metadata is corrupted, or there was a manual
        setup of the data palette, this function can be used to set
        the workspace metadata to the specified palette in that workspace
        by name or ID.  If you omit the name_or_id, then the code will
        search for an existing data palette in that workspace.  Be careful
        with this one- you could thrash your palette!
        :param params: instance of type "SetPaletteForWsParams" -> structure:
           parameter "workspace" of type "ws_name_or_id", parameter
           "palette_name_or_id" of String
        :returns: instance of type "SetPaletteForWsResult" -> structure:
        """
        return self._client.run_job('DataPaletteService.set_palette_for_ws',
                                    [params], self._service_ver, context)

    def status(self, context=None):
        return self._client.run_job('DataPaletteService.status',
                                    [], self._service_ver, context)

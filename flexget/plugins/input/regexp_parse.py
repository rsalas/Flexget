from __future__ import unicode_literals, division, absolute_import
import re
import logging
import os
from flexget.entry import Entry
from flexget.utils.cached_input import cached
from flexget.plugin import register_plugin, internet

log = logging.getLogger('regexp_parse')


class RegexpParse(object):

    FLAG_VALUES = {'DEBUG': re.DEBUG,
                   'I': re.I,
                   'IGNORECASE': re.IGNORECASE,
                   'L': re.L,
                   'LOCALE': re.LOCALE,
                   'M': re.M,
                   'MULTILINE': re.MULTILINE,
                   'S': re.S,
                   'DOTALL': re.DOTALL,
                   'U': re.U,
                   'UNICODE': re.UNICODE,
                   'X': re.X,
                   'VERBOSE': re.VERBOSE
                   }

    def __init__(self):
        self.required = []

    def validator(self):
        from flexget import validator
        root = validator.factory('dict')

        root.accept('url', key='source', required=True)
        root.accept('file', key='source', required=True)

	#sections to divied source into
	sections_regexp_lists = root.accept('list', key='sections')
        section_regexp_list = sections_regexp_lists.accept('dict', required=True)
        section_regexp_list.accept('regexp', key='regexp', required=True)
        section_regexp_list.accept('text', key='flags')
	
	keys = root.accept('dict', key='keys', required=True)

	#required key need to specify for validator
        title = keys.accept('dict', key='title', required=True)
        title.accept('boolean', key='required')
        regexp_list = title.accept('list', key='regexps', required=True)
        regexp = regexp_list.accept('dict', required=True)
        regexp.accept('regexp', key='regexp', required=True)
        regexp.accept('text', key='flags')

	#required key need to specify for validator
        url = keys.accept_any_key('dict', key='url', required=True)
        url.accept('boolean', key='required')
        regexp_list = url.accept('list', key='regexps', required=True)
        regexp = regexp_list.accept('dict', required=True)
        regexp.accept('regexp', key='regexp', required=True)
        regexp.accept('text', key='flags')

	#accept any other key the user wants to use
        key = keys.accept_any_key('dict')
        key.accept('boolean', key='required')
        regexp_list = key.accept('list', key='regexps', required=True)
        regexp = regexp_list.accept('dict', required=True)
        regexp.accept('regexp', key='regexp', required=True)
        regexp.accept('text', key='flags')

        return root

    def flagstr_to_flags(self, flag_str):
	"""turns a comma seperated list of flags into the int value"""
        COMBIND_FLAGS = 0
        split_flags = flag_str.split(',')
        for flag in split_flags:
            COMBIND_FLAGS = COMBIND_FLAGS | RegexParse.FLAG_VALUES[flag.strip()]
        return COMBIND_FLAGS

    def compile_regexp_dict_list(self, re_list):
	"""turns a list of dicts containing regexps information into a list of compiled regexps."""
        compiled_regexps = []
        for dic in re_list:
            flags = 0
            if 'flags' in dic:
                flags = self.flagstr_to_flags(dic['flags'])
            compiled_regexps.append(re.compile(dic['regex'], flags))
        return compiled_regexps

    def isvalid(self, entry):
	"""checks to make sure that all required fields are present in the entry"""
        for key in self.required:
            if key not in entry:
                return False
        return entry.isvalid()

    @cached('text')
    @internet(log)
    def on_task_input(self, task, config):

	entries = []
	
        url = config['source']

        #if it's a file open it and read into content
        if os.path.isfile(os.path.expanduser(url)):
            content = open(url).read()
	#else use requests to get the data
        else:
            content = task.requests.get(url).text
	
        sections = []
        seperators = config.get('sections')
        if seperators:
            for sep in seperators:
		print sep
                flags = 0
                if 'flags' in sep:
                    flags = self.flagstr_to_flags(sep['flags'])
                sections.extend(re.findall(sep['regexp'], content, flags))

        #no seperators just do work on the whole content
        else:
            sections.append(content)

        #holds all the regex in a dict for the field they are trying to fill
        key_to_regexps = {}

	#put every key in keys into the rey_to_regexps list
        for key, value in config['keys'].iteritems():
            key_to_regexps[key] = self.compile_regexp_dict_list(value['regexs'])
            if 'required' in value and value['required']:
                self.required.append(key)

        entries = []
        for section in sections:
            entry = Entry()
            for key, regexps in key_to_regexps.iteritems():
                for regexp in regexps:
                    m = regex.search(section)
                    if m:
                        entry[key] = m.group(0)
                        break
            if self.isvalid(entry):
                entries.append(entry)
	
        return entries


register_plugin(RegexpParse, 'regexp_parse', api_ver=2)

#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import plistlib
import re
import shutil
import subprocess

from tempfile import mkdtemp
from formats_common import *

enable = True
format = 'Mac'
description = 'Dictionary.app (.dictionary)'
extentions = ('.dictionary',)
readOptions = ()
writeOptions = ()
supportsAlternates = False

def _id_of_dict(dict_name):
    # create a camel case name as suggested by
    # https://developer.apple.com/library/mac/#qa/qa1373/_index.html
    return ''.join(w.capitalize() for w in re.split('\W+', dict_name))

def _id_of_word(word):
    return word.replace(' ', '_').replace('\'', '_')

ref_pattern = re.compile('<A href="bword://(.+)">(.+)</A>')
def _replace_hrefs(matched):
    return '<a href="x-dictionary:r:{word_id}"><b>{text}</b></a>'.format(word_id=_id_of_word(matched.group(1)), text=matched.group(2))

def _def_of_item(item):
    word, defi = item[:2]
    body = '<h1>{word}</h1>'.format(word=word)
    pr = None
    if defi[0] == '[':
        end = defi.find(']')
        pr = defi[1:end]
        defi = defi[end:]
        body += '''
	<span class="syntax"><span d:pr="1">| {pr} |</span></span>'''.format(pr=pr)
    defi = ref_pattern.sub(_replace_hrefs, defi)
    body += '''
		<div>
			{defi}
		</div>'''.format(defi=defi)
    return body

def write_xml(glos, filename):
    f = open(filename, 'w')
    f.write('''<?xml version="1.0" encoding="UTF-8"?>
<d:dictionary xmlns="http://www.w3.org/1999/xhtml" xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng">''')

    for item in glos.data:
        word, defi = item[:2]
        f.write('''
	<d:entry id="{word_id}" d:title="{word}">
		<d:index d:value="{word}"/>
		{body}
	</d:entry>'''.format(word_id=_id_of_word(word),
                         word=word,
                         body=_def_of_item(item)))
    f.write('''\n</d:dictionary>\n''')
    f.close()

def write_plist(glos, filename):
    dict_name = glos.getInfo('name').replace('_', ' ')
    copyright = glos.getInfo('copyright') or glos.getInfo('description')
    plist = {'CFBundleDisplayName': dict_name,
             'CFBundleName': _id_of_dict(dict_name),
             'CFBundleIdentifier': 'com.apple.dictionary.%s' % _id_of_dict(dict_name),
             'CFBundleShortVersionString': glos.getInfo('version'),
             'CFBundleDevelopmentRegion': glos.getInfo('targetLang'),
             'DCSDictionaryCopyright': copyright.decode('utf-8'),
             'DCSDictionaryManufacturerName': glos.getInfo('author')}
    plistlib.writePlist(plist, filename)

def write_css(glos, filename):
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'AppleDictionary.css')
    shutil.copy(css_path, filename)

DEBUG = True
def write(glos, filename):
    dict_dir = mkdtemp(prefix='convert-dict.')
    try:
        dict_files = dict((ext, os.path.join(dict_dir, 'Dict' + ext))
                          for ext in ['.xml', '.css', '.plist'])
        write_plist(glos, dict_files['.plist'])
        write_xml(glos, dict_files['.xml'])
        write_css(glos, dict_files['.css'])
        env = {'LANG': 'en_US.UTF-8'}       # for better looking error messages
        build_dict = '/Developer/Extras/Dictionary Development Kit/bin/build_dict.sh'
        if 'DICT_BUILD_TOOL_DIR' in os.environ:
            dict_build_tool_dir = os.environ['DICT_BUILD_TOOL_DIR']
            env['DICT_BUILD_TOOL_DIR'] = dict_build_tool_dir
            build_dict = os.path.join(dict_build_tool_dir, 'build_dict.sh')
        dict_name = _id_of_dict(glos.getInfo('name')),
        args = [build_dict, '-v 10.6',
                dict_name,
                dict_files['.xml'], dict_files['.css'], dict_files['.plist']]
        if subprocess.call(args + dict_files.values(), env=env, cwd=dict_dir):
            raise Exception("failed to build_dict.sh")
        shutil.move(os.path.join(dict_dir, 'objects', dict_name + '.dictionary'),
                    filename)
    except Exception as e:
        print "failed to convert dictionary: ", e
    finally:
        if not DEBUG:
            shutil.rmtree(dict_dir)

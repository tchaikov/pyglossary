#!/usr/bin/python
# -*- coding: utf-8 -*-
##  glossary.py 
##
##  Copyright © 2008-2010 Saeed Rasooli <saeed.gnu@gmail.com>  (ilius)
##  This file is part of PyGlossary project, http://sourceforge.net/projects/pyglossary/
##
##  This program is a free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 3, or (at your option)
##  any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License along
##  with this program. Or on Debian systems, from /usr/share/common-licenses/GPL
##  If not, see <http://www.gnu.org/licenses/gpl.txt>.

VERSION = '2012.01.25'

licenseText='''PyGlossary - A tool for workig with dictionary databases
Copyright © 2008-2010 Saeed Rasooli
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License,  or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. Or on Debian systems, from /usr/share/common-licenses/GPL. If not, see <http://www.gnu.org/licenses/gpl.txt>.'''


homePage = 'http://sourceforge.net/projects/pyglossary'

import os, sys, platform, time, subprocess, shutil, re
from os.path import splitext, isdir
from os.path import split as path_split
from os.path import join as path_join

from text_utils import myRaise, printAsError, faEditStr, replacePostSpaceChar, removeTextTags,\
                       takeStrWords, findWords, findAll, addDefaultOptions

import warnings
warnings.resetwarnings() ## ??????

srcDir = ''
if sys.argv[0]:
  srcDir = os.path.dirname(sys.argv[0])
'''
if not srcDir:
  if __file__:
    srcDir = os.path.dirname(__file__)
'''
if not srcDir:
  srcDir = '/usr/share/pyglossary/src'

rootDir = os.path.dirname(srcDir)

if sys.version_info[:2] == (2, 5): ## ???????????????????????
  libDir = path_join(rootDir, 'dependencies', 'py2.5-lib')
  if isdir(libDir):
    sys.path.append(libDir)
  ########
  libDir = path_join(rootDir, 'lib')
  if isdir(libDir):
    sys.path.append(libDir)

plugDir = path_join(rootDir, 'plugins')
if isdir(plugDir):
  sys.path.append(plugDir)
else:
  printAsError('invalid plugin directory %r'%plugDir)
  plugDir = ''


psys = platform.system()


if os.sep=='/': ## Operating system is Unix-Like
  homeDir = os.getenv('HOME')
  user    = os.getenv('USER')
  tmpDir  = '/tmp'
  ## os.name == 'posix' ## ????
  if psys=='Darwin':## MacOS X
    confPath = homeDir + '/Library/Preferences/PyGlossary' ## OR '/Library/PyGlossary'
    ## os.environ['OSTYPE']   == 'darwin10.0'
    ## os.environ['MACHTYPE'] == 'x86_64-apple-darwin10.0'
    ## platform.dist()        == ('', '', '')
    ## platform.release()     == '10.3.0'
  else:## GNU/Linux, ...
    confPath = homeDir + '/.pyglossary'
elif os.sep=='\\': ## Operating system is Windows
  homeDir = os.getenv('HOMEDRIVE') + os.getenv('HOMEPATH')
  user    = os.getenv('USERNAME')
  tmpDir  = os.getenv('TEMP')
  confPath = os.getenv('APPDATA') + '\\' + 'PyGlossary'
else:
  raise RuntimeError('Unknown path seperator(os.sep=="%s"), unknown operating system!'%os.sep)

get_ext = lambda path: splitext(path)[1].lower()




class Glossary:
  infoKeysAlias=(## Should be change according to a plugin???
    ('name'      , 'title'     , 'dbname'   , 'bookname'),
    ('sourceLang', 'inputlang' , 'origlang'),
    ('targetLang', 'outputlang', 'destlang'),
    ('copyright' , 'license'   )
  )
  readFormats=[]
  writeFormats=[]
  formatsDesc={}
  formatsExt={}
  formatsReadOptions={}
  formatsWriteOptions={}
  readExt    = [formatsExt[f] for f in readFormats]
  writeExt   = [formatsExt[f] for f in writeFormats]
  readDesc   = [formatsDesc[f] for f in readFormats]
  writeDesc  = [formatsDesc[f] for f in writeFormats]
  descFormat = dict([(formatsDesc[f], f) for f in formatsDesc.keys()])
  descExt    = dict([(formatsDesc[f], formatsExt[f][0]) \
                     for f in formatsDesc.keys()])
  #extFormats=dict([ (formatsExt[f], f) for f in formatsExt.keys() ])
  if plugDir:
    for f in os.listdir(plugDir):
      if f[-3:]!='.py':
        continue
      modName = f[:-3]
      mod = __import__(modName)
      try:
        if not mod.enable:
          continue
      except AttributeError:
        continue
      #print('loading plugin module %s'%modName)
      format = mod.format
      ext    = mod.extentions
      if isinstance(ext, basestring):
        ext = (ext,)
      elif not isinstance(ext, tuple):
        ext = tuple(ext)
      try:
        desc = mod.description
      except AttributeError:
        desc = '%s (%s)'%(format, ext[0])
      descFormat[desc] = format
      descExt[desc] = ext[0]
      formatsExt[format] = ext
      formatsDesc[format] = desc
      if hasattr(mod, 'read'):
        exec('read%s = mod.read'%format)
        readFormats.append(format)
        readExt.append(ext)
        readDesc.append(desc)
        formatsReadOptions[format] = mod.readOptions
      if hasattr(mod, 'write'):
        exec('write%s = mod.write'%format)
        writeFormats.append(format)
        writeExt.append(ext)
        writeDesc.append(desc)
        formatsWriteOptions[format] = mod.writeOptions
      del f, mod, format, ext, desc


  def __init__(self, info=[], data=[], resPath=''):
    self.info = []
    self.setInfos(info, True)
    # a list if tuples: ('key', 'definition') or ('key', 'definition', dict() )
    # in general we should assume the tuple may be of arbitrary length >= 2
    # known dictionary keys:
    #   data[i][2]['alts'] - list of alternates, filled by bgl reader
    self.data = data
    #####
    self.filename = ''
    self.resPath = resPath
    self.ui = None

  __str__ = lambda self: 'glossary.Glossary'

  def copy(self):
    g = Glossary(self.info[:], self.data[:])
    g.filename = self.filename
    g.resPath = self.resPath
    g.ui = self.ui ## ???
    return g

  def infoKeys(self):
    return [ t[0] for t in self.info ]

  #def formatInfoKeys(self, format):## FIXME

  def getInfo(self, key):
    lkey = str(key).lower()
    for group in Glossary.infoKeysAlias:
      if not isinstance(group, (list, tuple)):
        raise TypeError, 'group=%s'%group
      if (key in group) or (lkey in group):
        for skey in group:
          for t in self.info:
            if t[0]==skey:
              return t[1]
    for t in self.info:
      if t[0]==key or t[0].lower()==lkey:
        return t[1]
    return ''

  def setInfo(self, key, value):
    lkey = str(key).lower()
    for group in Glossary.infoKeysAlias:
      if not isinstance(group, (list, tuple)):
        raise TypeError, 'group=%s'%group
      if (key in group) or (lkey in group):
        skey=group[0]
        for i in xrange(len(self.info)):
          if self.info[i][0]==skey:
            self.info[i]=(self.info[i][0],value)
            return
        for i in xrange(len(self.info)):
          if self.info[i][0] in group:
            self.info[i]=(self.info[i][0],value)
            return
    for i in xrange(len(self.info)):
      if self.info[i][0]==key or self.info[i][0].lower()==lkey:
          self.info[i]=(self.info[i][0],value)
          return
    self.info.append([key,value])

  def setInfos(self, info, setAll=False):
    for t in info:
      self.setInfo(t[0], t[1])
    if setAll:
      for key in self.infoKeys():
        if self.getInfo(key)=='':
          self.setInfo(key, '')

  def removeTags(self, tags):
    n = len(self.data)
    for i in xrange(n):
      self.data[i] = (self.data[i][0], removeTextTags(self.data[i][1], tags)) + self.data[i][2:]

  def lowercase(self):
    for i in xrange(len(self.data)):
      self.data[i] = (self.data[i][0].lower(), self.data[i][1]) + self.data[i][2:]

  def capitalize(self):
    for i in xrange(len(self.data)):
      self.data[i] = (self.data[i][0].capitalize(), self.data[i][1]) + self.data[i][2:]

  def read(self, filename, format='', **options):
    delFile=False
    ext = splitext(filename)[1]
    ext = ext.lower()
    if ext in ('.gz', '.bz2', '.zip'):
      if ext=='.bz2':
        (output, error) = subprocess.Popen(
          ['bzip2', '-dk', filename],
          stdout=subprocess.PIPE
        ).communicate()
        ## -k ==> keep original bz2 file
        ## bunzip2 ~= bzip2 -d
        if error:
          printAsError('%s\nfail to decompress file "%s"'%(error, filename))
          return False
        else:
          filename = filename[:-4]
          ext = splitext(filename)[1]
          delFile = True
      elif ext=='.gz':
        (output, error) = subprocess.Popen(
          ['gzip', '-dc', filename],
          stdout=subprocess.PIPE
        ).communicate()
        ## -c ==> write to stdout (because we want to keep original gz file)
        ## gunzip ~= gzip -d
        if error:
          printAsError('%s\nfail to decompress file "%s"'%(error, filename))
          return False
        else:
          filename = filename[:-3]
          open(filename, 'w').write(output)
          ext = splitext(filename)[1]
          delFile = True
      elif ext=='.zip':
        (output, error) = subprocess.Popen(
          ['unzip', filename, '-d', os.path.dirname(filename)],
          stdout=subprocess.PIPE
        ).communicate()
        if error:
          printAsError('%s\nfail to decompress file "%s"'%(error, filename))
          return False
        else:
          filename = filename[:-4]
          ext = splitext(filename)[1]
          delFile = True
    if format=='':
      for key in Glossary.formatsExt.keys():
        if ext in Glossary.formatsExt[key]:
          format = key
      if format=='':
        #if delFile:
        #  os.remove(filename)
        printAsError('Unknown extension "%s" for read support!'%ext)
        return False
    validOptionKeys = self.formatsReadOptions[format]
    for key in options.keys():
      if not key in validOptionKeys:
        printAsError('Invalid read option "%s" given for %s format'%(key, format))
        del options[key]
    getattr(self, 'read%s'%format).__call__(filename, **options)
    
    (filename_nox, ext) = splitext(filename)
    if ext.lower() in self.formatsExt[format]:
      filename = filename_nox
    self.filename = filename
    if self.getInfo('name') == '':
      self.setInfo('name', path_split(filename)[1])

    if delFile:
      os.remove(filename)
    return True


  def write(self, filename, format='', **options):
    if not filename:
      printAsError('Invalid filename %r'%filename)
      return False
    ext = ''
    (filename_nox, fext) = splitext(filename)
    fext = fext.lower()
    if fext in ('.gz', '.bz2', '.zip'):
      zipExt = fext
      filename = filename_nox
      fext = splitext(filename)[1].lower()
    else:
      zipExt = ''
    del filename_nox
    if format:
      try:
        ext = Glossary.formatsExt[format][0]
      except KeyError:
        myRaise()
        format = '' ## ?????
    if not format:
      items = Glossary.formatsExt.items()
      for (fmt, extList) in items:
        for e in extList:
          if format==e[1:] or format==e:
            format = fmt
            ext = e
            break
        if format:
          break
      if not format:
        for (fmt, extList) in items:
          if filename==fmt:
            format = filename
            ext = extList[0]
            filename = self.filename + ext
            break
          for e in extList:
            if filename==e[1:] or filename==e:
              format = fmt
              ext = e
              filename = self.filename + ext
              break
          if format:
            break
      if not format:
        for (fmt, extList) in items:
          if fext in extList:
            format = fmt
            ext = fext
    if not format:
      printAsError('Unable to detect write format!')
      return False
    if isdir(filename):
      #filename = path_join(filename, path_split(self.filename)[1]+ext)
      filename = path_join(filename, self.filename+ext)
    validOptionKeys = self.formatsWriteOptions[format]
    for key in options.keys():
      if not key in validOptionKeys:
        printAsError('Invalid write option "%s" given for %s format'%(key, format))
        del options[key]
    print 'filename=%s'%filename
    getattr(self, 'write%s'%format).__call__(filename, **options)
    if zipExt:
      try:
        os.remove('%s%s'%(filename, zipExt))
      except OSError:
        pass
      if zipExt=='.gz':
        (output, error) = subprocess.Popen(
          ['gzip', filename],
          stdout=subprocess.PIPE
        ).communicate()
        if error:
          printAsError('%s\nfail to compress file "%s"'%(error, filename))
      elif zipExt=='.bz2':
        (output, error) = subprocess.Popen(
          ['bzip2', filename],
          stdout=subprocess.PIPE
        ).communicate()
        if error:
          printAsError('%s\nfail to compress file "%s"'%(error, filename))
      elif zipExt=='.zip':
        (dirn, name) = path_split(filename)
        initCwd = os.getcwd()
        os.chdir(dirn)
        (output, error) = subprocess.Popen(
          ['zip', filename+'.zip', name, '-m'],
          stdout=subprocess.PIPE
        ).communicate()
        if error:
          printAsError('%s\nfail to compress file "%s"'%(error, filename))
        os.chdir(initCwd)

  def writeTxt(self, sep, filename='', writeInfo=True, rplList=[], ext='.txt', head=''):
    if not filename:
      filename = self.filename + ext
    txt = head
    if writeInfo:
      for t in self.info:
        #??????????????????????????
        inf = t[1]
        for rpl in rplList:
          inf = inf.replace(rpl[0], rpl[1])
        txt += ('##' + t[0] + sep[0] + inf + sep[1])
        #inf = self.getInfo(t[0])
        #if inf!='':
        #  try:
        #    txt+=('##' + t[0] + sep[0] + inf + sep[1])
        #  except:
        #    myRaise(__file__)
        #    printAsError('Error on writing info line for "%s"'%t[0])
    for item in self.data:
      (word, defi) = item[:2]
      if word.startswith('#'):
        continue
      if self.getPref('enable_alts', True):
        try:
          alts = item[2]['alts']
        except:
          pass
        else:
          if alts:
            word = '|'.join([word] + alts)
      for rpl in rplList:
        defi = defi.replace(rpl[0], rpl[1])
      try:
        line = word + sep[0] + defi + sep[1]
        txt += line
      except:
        myRaise(__file__)
        printAsError('Error on writing line for word "%s"'%word)
        continue
    if filename==None:
      return txt
    with open(filename, 'wb') as fp:
      fp.write(txt)
    return True



  def writeDict(self, filename='', writeInfo=False):
    ## Used in '/usr/share/dict/' for some dictionarys such as 'ding'.
    self.writeTxt((' :: ', '\n'), filename, writeInfo,
                  (('\n', '\\n'),), '.dict')


  def printTabfile(self):
    for item in self.data:
      (word, defi) = item[:2]
      defi = defi.replace('\n', '\\n')
      try:
        print(word+'\t'+defi)
      except:
        myRaise(__file__)


  ###################################################################
  takeWords = lambda self: [ item[0] for item in self.data ]


  def takeOutputWords(self, opt={}):
    words=takeStrWords(' '.join([item[1] for item in self.data]), opt)
    words.sort()
    words=removeRepeats(words)
    return words

  getInputList = lambda self: [x[0] for x in self.data]

  getOutputList = lambda self: [x[1] for x in self.data]

  def simpleSwap(self):
    # loosing item[2:]
    return Glossary(self.info[:], [ (item[1], item[0]) for item in self.data ])

  def attach(self, other):# only simplicity attach two glossaries (or more that others be as a list).
  # no ordering. Use when you split input words to two(or many) parts after ordering.
    try:
      other.data, other.info
    except:
      if isinstance(other, (list, tuple)):
        if len(other)==0:
          return self
        if len(other)==1:
          return self.attach(other[0])
        return self.attach(other[0]).attach(other[1:])
      else:
        return self
    newName = '"%s" attached to "%s"'%( self.getInfo('name') , other.getInfo('name') )
    ng = Glossary(  [('name',newName)]  , self.data + other.data)
    ## here attach and set info of two glossary ## FIXME
    return ng

  def merge(self, other):
    try:
      other.data, other.info
    except:
      if isinstance(other, (list, tuple)):
        if len(other)==0:
          return self
        if len(other)==1:
          return self.merge(other[0])
        return self.merge(other[0]).merge(other[1:])
      else:
        raise TypeError, 'bad argument given to merge! other="%s"'%other
    newName = '"%s" merged with "%s"'%( self.getInfo('name') , other.getInfo('name') )
    new = Glossary(  [('name',newName)]  )
    new.data = self.data + other.data
    new.data.sort()
    return new


  def deepMerge(self, other, sep="\n"):#merge two optional glossarys nicly. no repets in words of result glossary
    try:
      other.data, other.info
    except:
      if isinstance(other, (list, tuple)):
        if len(other)==0:
          return self
        if len(other)==1:
          return self.deepMerge(other[0])
        return self.deepMerge(other[0]).deepMerge(other[1:])
      else:
        raise TypeError, 'bad argument given to deepMerge! other="%s"'%other
    newName = '"%s" deep merged with "%s"'%( self.getInfo('name') , other.getInfo('name') )
    new = Glossary(  [('name',newName)]  )
    data = list(self.data + other.data)
    data.sort(lambda t1, t2: cmp(t1[0], t2[0]))
    n=len(data)
    i=0
    while i<len(data)-1:
      if data[i][0]==data[i+1][0]:
        if data[i][1]!=data[i+1][1]:
          data[i] = ( data[i][0], data[i][1]+sep+data[i+1][1] )
        data.pop(i+1)
      else:
        i += 1
    new.data=data
    return new


  def __add__(self, other):
    return self.merge(other) 


  def searchWordInDef(self, st, opt):
    #seachs word 'st' in meanings(definitions) of the glossary 'self'
    defOpt={'minRel':0.0, 'maxNum':100, 'sep':commaFa, 'matchWord':True, 'showRel':'Percent'}
    opt = addDefaultOptions(opt, defOpt)
    sep = opt['sep']
    matchWord = opt['matchWord']
    maxNum = opt['maxNum']
    minRel = opt['minRel']
    defs = opt['includeDefs']
    outRel = []
    for item in self.data:
      (word, defi) = item[:2]
      defiParts = defi.split(sep)
      if defi.find(st)==-1:
        continue
      rel=0 #relationship value of word (as a float number between 0 and 1
      for part in defiParts:
        for ch in sch:
          part = part.replace(ch, ' ')
        pRel = 0 # part relationship
        if matchWord:
           pNum = 0
           partWords = takeStrWords(part)
           pLen = len(partWords)
           if pLen==0:
             continue
           for pw in partWords:
             if pw==st:
               pNum += 1
           pRel=float(pNum)/pLen  # part relationship
        else:
           pLen = len(part.replace(' ', ''))
           if pLen==0:
             continue
           pNum = len(findAll(part, st))*len(st)
           pRel=float(pNum)/pLen  # part relationship
        if pRel > rel:
          rel = pRel
      if rel <= minRel:
        continue
      if defs:
        outRel.append((word,rel,defi))
      else:
        outRel.append((word,rel))
    #sortby_inplace(outRel, 1, True)##???
    outRel.sort(key=1, reverse=True)
    n=len(outRel)
    if n > maxNum > 0:
      outRel=outRel[:maxNum]
      n=maxNum
    num=0
    out=[]
    if defs:
      for j in xrange(n):
        numP=num
        (w,num,m)=outRel[j]
        m = m.replace('\n', '\\n').replace('\t', '\\t')
        onePer=int(1.0/num)
        if onePer==1.0:
          out.append('%s\\n%s'%(w,m))
        elif opt['showRel']=='Percent':
          out.append('%s(%%%d)\\n%s' % ( w, 100*num , m ))
        elif opt['showRel']=='Percent At First':
          if num==numP:
            out.append('%s\\n%s'%(w,m))
          else:
            out.append('%s(%%%d)\\n%s' % ( w, 100*num , m ))
        else:
          out.append('%s\\n%s'%(w,m))
      return out
    for j in xrange(n):
      numP=num
      (w,num)=outRel[j]
      onePer=int(1.0/num)
      if onePer==1.0:
        out.append(w)
      elif opt['showRel']=='Percent':
        out.append('%s(%%%d)' % ( w, 100*num ))
      elif opt['showRel']=='Percent At First':
        if num==numP:
          out.append(w)
        else:
          out.append('%s(%%%d)' % ( w, 100*num ))
      else:
        out.append(w)
    return out


  def reverseDic(self, wordsArg=None, opt={}):
    defOpt={
    'matchWord'         :True,
    'showRel'           :'None',
    'includeDefs'       :False,
    'background'        :False,
    'reportStep'        :300,
    'autoSaveStep'      :1000, ## set this to zero to disable auto saving.
    'savePath'          :''}
    opt = addDefaultOptions(opt, defOpt)
    self.stoped = False
    ui=self.ui
    try:
      c = self.continueFrom
    except AttributeError:
      c = 0
    savePath = opt['savePath']
    if c==-1:
      print('c=%s'%c)
      return
    elif c==0:
      saveFile = open(savePath, 'wb')
      ui.progressStart()
      ui.progress(0.0, 'Starting...')
    elif c>0:
      saveFile = open(savePath, 'ab')
    if wordsArg==None:
      words = self.takeOutputWords()
    elif isinstance(wordsArg, file):
      words = wordsArg.read().split('\n')
    elif isinstance(wordsArg, (list, tuple)):
      words = wordsArg[:]
    elif isinstance(wordsArg, basestring):
      words = open(wordsArg).read().split('\n')
    else:
      raise TypeError, 'Argumant wordsArg to function reverseDic is not valid!'
    autoSaveStep = opt['autoSaveStep']
    if opt['savePath']=='':
      opt['savePath'] = self.getInfo('name')+'.txt'
    revG = Glossary(self.info[:])
    revG.setInfo('name', self.getInfo('name')+'_reversed')
    revG.setInfo('inputlang' , self.getInfo('outputlang'))
    revG.setInfo('outputlang', self.getInfo('inputlang'))
    wNum = len(words)
    #steps = opt['reportStep']
    #div = 0
    #mod = 0
    #total = int(wNum/steps)
    """
    if c==0:
      print('Number of input words:', wNum)
      print('Reversing glossary...')
    else:
      print('continue reversing from index %d ...'%c)
    """
    t0 = time.time()
    if ui==None:
      print('passed ratio         time:  passed       remain          total       process')
    n = len(words)
    for i in xrange(c, n):
       word = words[i]
       rat = float(i+1)/n
       ui.progress(rat, '%d / %d words completed'%(i,n))
       if ui.reverseStop:
         saveFile.close()  ## if with KeyboardInterrupt it will be closed ??????????????
         self.continueFrom = i
         self.stoped = True
         #thread.exit_thread()
         return
       else:
         self.i = i
       """
       if mod == steps:
         mod = 0 ; div += 1
         t = time.time()
         dt = t-t0
         tRem = (total-div)*dt/div ## (n-i)*dt/n
         rat = float(i)/n
         if ui==None:
           print('%4d / %4d               %8s\t%8s\t%8s\t%s'%(div,total,timeHMS(dt),\
             timeHMS(tRem),timeHMS(dt+tRem),sys.argv[0]))
         else:
           #############  ??????????????????????????????????????????????????????????????
           #ui.progressbar.set_text('%d/%d words completed (%%%2f) remaining %d seconds'%(i,n,rat*100,tRem))
           ui.progressbar.update(rat)
           while gtk.events_pending():
             gtk.main_iteration_do(False)
       else:
         mod += 1
       """
       if autoSaveStep>0 and i%autoSaveStep==0 and i>0:
         saveFile.close()
         saveFile = open(savePath, 'ab')
       result = self.searchWordInDef(word, opt)
       if len(result)>0:
         try:
           if opt['includeDefs']:
             defi = '\\n\\n'.join(result)
           else:
             defi = ', '.join(result) + '.'
         except:
           open('result', 'wb').write(str(result))
           myRaise(__file__)
           return False
         if autoSaveStep>0:
           saveFile.write('%s\t%s\n'%(word, defi))
         else:
          revG.data.append((word, defi)) 
       if autoSaveStep>0 and i==n-1:
         saveFile.close()
    if autoSaveStep==0:
      revG.writeTabfile(opt['savePath'])
    ui.r_finished()
    ui.progressEnd()
    return True


  def reverseDic_ext(self, wordsArg=None, opt={}):
    from _reverse_dic import search
    tabStr=self.writeTabfile(filename=None)
    defOpt={
    'matchWord':True,
    'showRel':'None',
    'background':False,
    'reportStep':300,
    'autoSaveStep':1000, ## set this to zero to disable auto saving.
    'savePath':'',
    'sep':commaFa}
    opt = addDefaultOptions(opt, defOpt)
    self.stoped = False
    ui=self.ui
    try:
      c = self.continueFrom
    except AttributeError:
      c = 0
    if c==-1:
      print('c=%s'%c)
      return
    elif c==0:
      ui.progress(0, 'Starting....')
    if wordsArg==None:
      words = self.takeOutputWords()
    elif isinstance(wordsArg, file):
      words = [ w[:-1] for w in wordsArg.readlines() ]
    elif isinstance(wordsArg, (list, tuple)):
      words = wordsArg[:]
    elif isinstance(wordsArg, basestring):
      fp = open(wordsArg)
      words = [ w[:-1] for w in fp.readlines() ]
      fp.close()
    else:
      raise TypeError, 'Argumant wordsArg to function reverseDic is not valid!'
    autoSaveStep = opt['autoSaveStep']
    if opt['savePath']=='':
      opt['savePath']=self.getInfo('name')+'.txt'
    savePath = opt['savePath']
    if c > 0:
      saveFile = open(savePath, 'ab')
    else:
      saveFile = open(savePath, 'wb')
      ui.progressStart()
    revG = Glossary(self.info[:])
    revG.setInfo('name', self.getInfo('name')+'_reversed')
    revG.setInfo('inputlang' , self.getInfo('outputlang'))
    revG.setInfo('outputlang', self.getInfo('inputlang'))
    wNum=len(words)
    #steps = opt['reportStep']
    #div = 0
    #mod = 0
    #total = int(wNum/steps)
    if c==0:
      print('Number of input words:', wNum)
      print('Reversing glossary...')
    else:
      print('continue reversing from index %d ...'%c)
    t0=time.time()
    if ui==None:
      print('passed ratio         time:  passed       remain          total       process')
    n = len(words)
    for i in xrange(c, n):
       word = words[i]
       rat = float(i+1)/n
       ui.progress(rat, '%d / %d words completed'%(i,n))
       if ui.reverseStop:
         saveFile.close()
         self.continueFrom = i
         self.stoped = True
         #thread.exit_thread()
         return
       if autoSaveStep>0 and i%autoSaveStep==0 and i>0:
         saveFile.close()
         saveFile = open(savePath, 'ab')
       result = search(tabStr,word,opt['minRel'],opt['maxNum'],opt['sep'],opt['matchWord'],opt['showRel'])
       if len(result)>0:
         new = ( word , result )
         if autoSaveStep>0:
           saveFile.write('%s\t%s\n'%new)
         else:
          revG.data.append(new) 
       if autoSaveStep>0 and i==n-1:
         saveFile.close()
    if autoSaveStep==0:
      revG.writeTabfile(opt['savePath'])
    ui.r_finished()
    ui.progressEnd()
    return True

  def replaceInDefinitions(self, replaceList, matchWord=False):
    if not matchWord:
      for rpl in replaceList:
        for i in xrange(len(self.data)):
           if self.data[i][1].find(rpl[0])>-1:
             self.data[i] = (self.data[i][0], self.data[i][1].replace(rpl[0], rpl[1])) + self.data[i][2:]
    else:
      num=0
      for rpl in replaceList:
        for j in xrange(len(self.data)):
          # words indexes
          wdsIdx = findWords(self.data[j][1], {'word':rpl[0]})
          for [i0,i1] in wdsIdx:
            self.data[j][1] = self.data[j][1][:i0] + rpl[1] + self.data[j][1][i1:]
            num += 1
      return num

  def takePhonetic_oxford_gb(self):
   phg = Glossary(self.info[:]) # phonetic glossary
   phg.setInfo('name', self.getInfo('name')+'_phonetic')
   for item in self.data:
     word=item[0]
     defi=item[1]
     if defi[0]!="/":
       continue
     #### Now set the phonetic to the `ph` variable.
     ph=""
     sep=["/ adj", "/ v", "/ n", "/ adv", "/adj", "/v", "/n", "/adv", "/ n","/ the"]
     for s in sep:
       i = defi.find(s,2,85)
       if i==-1:
         continue
       else:
         ph=defi[:i+1]
         break
     ph = ph.replace(';', '\t')\
            .replace(',', '\t')\
            .replace('     ', '\t')\
            .replace('    ', '\t')\
            .replace('  ', '\t')\
            .replace('//', '/')\
            .replace('\t/\t', '\t')\
            .replace('<i>US</i>\t', '\tUS: ')\
            .replace('<i>US</i>', '\tUS: ')\
            .replace('\t\t\t', '\t')\
            .replace('\t\t', '\t')\
     #      .replace('/', '')
     #      .replace('\\n ', '\\n')
     #      .replace('\\n  ', '\\n')
     if ph != "":
       phg.data.append((word, ph))
   return phg


  def getSqlLines(self, filename='', info=None, newline='\\n'):
    lines=[]
    infoDefLine = 'CREATE TABLE dbinfo ('
    infoList=[]
    #######################
    #keys=('name', 'author', 'version', 'direction', 'origLang', 'destLang', 'license', 'category', 'description')
    #for key in keys:
    #  inf = "'" + self.getInfo(key).replace('\'', '"').replace('\n',newline) + "'"
    #  infoList.append(inf)
    #  infoDefLine += '%s varchar(%d), '%(key, len(inf)+10)
    ######################
    if info==None:
      info = self.info
    for item in info:
      inf = "'" + item[1].replace("'", '"')\
                         .replace("\x00", '')\
                         .replace('\n', newline) + "'"
      infoList.append(inf)
      infoDefLine += '%s char(%d), '%(item[0], len(inf))
    ######################
    infoDefLine = infoDefLine[:-2] + ');'
    lines.append(infoDefLine)
    lines.append("CREATE TABLE word ('s_id' INTEGER PRIMARY KEY NOT NULL, 'wname' TEXT, 'wmean' TEXT);")
    lines.append('INSERT INTO dbinfo VALUES(%s);'%(','.join(infoList)))
    for i in xrange(len(self.data)):
      w = self.data[i][0].replace('\'', '"').replace('\n', newline)
      m = self.data[i][1].replace('\'', '"').replace('\n', newline)
      lines.append("INSERT INTO word VALUES(%d,'%s','%s');"%(i+1, w, m))
    lines.append("CREATE INDEX wnameidx ON word(wname);")
    #lines.append("COMMIT;")
    return lines

  def utf8ReplaceErrors(self):
    errors = 0
    for i in xrange(len(self.data)):
      (w, m) = self.data[i][:2]
      w = w.replace('\x00', '')
      m = m.replace('\x00', '')
      try:
        m.decode('utf-8')
      except UnicodeDecodeError:
        m = m.decode('utf-8', 'replace').encode('utf-8')
        errors += 1
      try:
        w.decode('utf-8')
      except UnicodeDecodeError:
        w = w.decode('utf-8', 'replace').encode('utf-8')
        errors += 1
      if len(self.data[i]) >= 3:
        d = self.data[i][2]
        if 'alts' in d:
          a = d['alts']
          for j in xrange(len(a)):
            a[j] = a[j].replace('\x00', '')
            try:
              a[j].decode('utf-8')
            except UnicodeDecodeError:
              a[j] = a[j].decode('utf-8', 'replace').encode('utf-8')
              errors += 1
        d = [d]
      else:
        d = []
      a = [w, m]
      a.extend(d)
      a.extend(self.data[i][3:])
      self.data[i] = a
    for i in xrange(len(self.info)):
      (w, m) = self.info[i]
      w = w.replace('\x00', '')
      m = m.replace('\x00', '')
      try:
        m.decode('utf-8')
      except UnicodeDecodeError:
        m = m.decode('utf-8', 'replace').encode('utf-8')
        errors += 1
      try:
        w.decode('utf-8')
      except UnicodeDecodeError:
        w = w.decode('utf-8', 'replace').encode('utf-8')
        errors += 1
      self.info[i] = (w, m)
    if errors:
      printAsError('There was %s number of invalid utf8 strings, invalid characters are replaced with "�"'%errors)

  def clean(self):
    d = self.data
    n = len(d)
    for i in range(n):
      # key must not contain tags, at least in bgl dictionary ???
      w = d[i][0].strip()
      m = d[i][1].strip()\
                 .replace('♦  ', '♦ ')
      
      m = re.sub("[\r\n]+", "\n", m)
      m = re.sub(" *\n *", "\n", m)

      """
      This code may correct snippets like:
      - First sentence .Second sentence. -> First sentence. Second sentence.
      - First clause ,second clause. -> First clause, second clause.
      But there are cases when this code have undesirable effects
      ( '<' represented as '&lt;' in HTML markup):
      - <Adj.> -> < Adj. >
      - <fig.> -> < fig. >
      """
      """
      for j in range(3):
        for ch in ',.;':
          m = replacePostSpaceChar(m, ch)
      """

      m = re.sub('♦\n+♦', '♦', m)
      if m.endswith('<p'):
        m = m[:-2]
      m = m.strip()
      if m.endswith(','):
        m = m[:-1]
      d[i] = (w, m) + d[i][2:]
    # remove items with empty keys and definitions
    d2 = []
    for item in d:
      if not item[0] or not item[1]:
        continue
      if len(item) >= 3:
        if 'alts' in item[2]:
          a = item[2]['alts']
          a2 = []
          for s in a:
            if s:
              a2.append(s)
          item[2]['alts'] = a2
      d2.append(item)
    self.data[:] = d = d2

  def faEdit(self):
    RLM = '\xe2\x80\x8f'
    for i in range(len(self.data)):
      (w, m) = self.data[i][:2]
      ## m = '\n'.join([RLM+line for line in m.split('\n')]) ## for GoldenDict
      self.data[i] = (faEditStr(w), faEditStr(m)) + self.data[i][2:]
    for i in range(len(self.info)):
      (w, m) = self.info[i]
      self.info[i] = (faEditStr(w), faEditStr(m))

  def uiEdit(self):
    p = self.ui.pref
    if p['sort']:
      self.data.sort()
    if p['lower']:
      self.lowercase()
    if p['remove_tags']:
      self.removeTags(p['tags'])
    langs = (self.getInfo('sourceLang') + self.getInfo('targetLang')).lower()
    if 'persian' in langs or 'farsi' in langs:
      self.faEdit()
    self.clean()
    if p['utf8_check']:
      self.utf8ReplaceErrors()

  def getPref(self, name, default):
    if self.ui:
      return self.ui.pref.get(name, default)
    else:
      return default

  def dump(self, dataPath):
    "Dump data into the file for debugging"
    with open(dataPath, 'wb') as f:
      for item in g.data:
        f.write('key = ' + item[0] + '\n')
        f.write('defi = ' + item[1] + '\n\n')

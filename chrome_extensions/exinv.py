import json
import os
import sys
import re


_ACCESS_ALL = '**Access your data on all websites**'

PERMISSIONS = {
    'plugins': 'Access all data on your computer and the websites you visit',
    'bookmarks': 'Read and modify your bookmarks',
    'history': 'Read and modify your browsing history',
    'topSites': 'Read and modify your browsing history',
    'tabs': 'Access your tabs and browsing activity',
    'webNavigation': 'Access your tabs and browsing activity',
    'contentSettings': 'Manipulate settings that specify whether websites can '
        'use features such as cookies, JavaScript, and plug-ins',
    'debugger': _ACCESS_ALL,
    'pageCapture': _ACCESS_ALL,
    'proxy': _ACCESS_ALL,
    'devtools_page': _ACCESS_ALL,
    'management': 'Manage your apps, extensions, and themes',
    'geolocation': 'Detect your physical location',
    'clipboardRead': 'Access data you copy and paste',
    'privacy': '**Manipulate privacy-related settings**',
    'signedInDevices': '**Access the list of your signed-in devices**',
    'ttsEngine': 'Access all text spoken using synthesized speech',
    'activeTab': None,
    'browsingData': None,
    'chrome://favicon/': None,
    'clipboardWrite': None,
    'contextMenus': None,
    'cookies': None,
    'experimental': None,
    'idle': None,
    'notifications': None,
    'storage': None,
    'unlimitedStorage': None,
    'webRequest': None,
    'webRequestBlocking': None,
    'fileSystem': 'Access your local filesystem',
    'identity': '**Access your signed-in identity**',
    'webview': None,
    'background': None,
    'networkingPrivate': '**Manage network connections**',
    'system.cpu': None,
    'tabCapture': _ACCESS_ALL,
    }


def cmpversion(a, b):
  """Compare versions the way chrome does."""
  def split_version(v):
    """Get major/minor of version."""
    if '.' in v:
      return v.split('.', 1)
    if '_' in v:
      return v.split('_', 1)
    return (v, '0')
  a_maj, a_min = split_version(a)
  b_maj, b_min = split_version(b)
  if a_maj == b_maj:
    return cmpversion(a_min, b_min)
  return int(a_maj) > int(b_maj)


def process_extensions(dirname=None):
  results = {}
  dirname = dirname or os.getcwd()
  for d in os.listdir(dirname):
    extdir = os.path.join(dirname, d)
    if os.path.isdir(extdir):
      extdata = process_extension(extdir)
      try:
        results.update(extdata)
      except TypeError:
        pass
  return results


def process_extension(extdir):
  # find the latest version
  sorted_versions = sorted(os.listdir(extdir), cmp=cmpversion, reverse=True)
  if not sorted_versions:
    return None
  max_version = sorted_versions[0]
  return process_manifest(os.path.join(extdir, max_version))


def process_manifest(extdir):
  manifest_file = os.path.join(extdir, 'manifest.json')
  manifest = json.load(open(manifest_file))
  name = manifest['name']
  if name.startswith('__MSG'):
    name = _translate_name(name, manifest['default_locale'], extdir)
  permissions = manifest.get('permissions', [])
  # TODO: support content_scripts
  if 'permissions' in manifest:
    return {name: permissions}
  return None


def _translate_name(name, locale, extdir):
  locale = json.load(open(os.path.join(extdir, '_locales', locale,
    'messages.json')))
  name = name.lstrip('__MSG_').rstrip('__')
  try:
    return locale[name]['message']
  except KeyError:
    name = name.lower()
    for k in locale.keys():
      if k.lower() == name:
        return locale[k]['message']
  return name


def translate_permissions(perms):
  translated = []
  for p in perms:
    translated.extend(_translate_permission(p))
  return sorted(set(translated))


def _translate_permission(perm):
  if isinstance(perm, dict):
    ret = []
    for p in perm.keys():
      ret.extend(_translate_permission(p))
    return ret
  try:
    p = PERMISSIONS[perm]
    if p:
      return [p]
    return []
  except KeyError:
    if _matches_all(perm):
      return [_ACCESS_ALL]
    return ['Access data on %s' % perm]


def _matches_all(path):
  return re.match(r'([A-Za-z]+://\*/\*.*|<all_urls>)', path.strip())


if __name__ == '__main__':
  if len(sys.argv) > 1:
    d = sys.argv[1]
  else:
    d = os.getcwd()
  permissions = process_extensions(d)
  for ext, perms in permissions.iteritems():
    translated = translate_permissions(perms)
    if translated:
      print '- %s' % ext
      for p in translated:
        print '    - %s' % p

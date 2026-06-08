import os
import sys
import django
from pathlib import Path
sys.path.insert(0, os.path.join(os.getcwd(), 'medcloud'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcloud.settings')
django.setup()
from django.template import engines
from django.template import loader
eng = engines['django']
print('dirs:', eng.dirs)
print('TEMPLATE_DIRS setting:', django.conf.settings.TEMPLATES[0]['DIRS'])
print('engine attrs:', [a for a in dir(eng.engine) if 'loader' in a.lower() or 'load' in a.lower()][:20])
print('engine class:', type(eng.engine))
try:
    loaders = eng.engine.template_loaders
    print('template_loaders attr found:', loaders)
except AttributeError as e:
    print('no template_loaders attr:', e)
try:
    loaders = eng.engine.loaders
    print('loaders attr found:', loaders)
except AttributeError as e:
    print('no loaders attr:', e)
print('--- selecting template ---')
t = loader.get_template('socialaccount/login.html')
print('selected origin:', t.origin.name)
print('exists custom file:', Path('medcloud/templates/socialaccount/login.html').exists())
print('exists account file:', Path('medcloud/templates/account/login.html').exists())

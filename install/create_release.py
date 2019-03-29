import os

version = ''

with open('../onionr/onionr.py', 'r') as f:
    version = f.read().split("ONIONR_VERSION = '")[1].split("'")[0]

version_tuple = tuple(ONIONR_VERSION.split('.'))

print('Current Onionr release version is %s (MAJOR.MINOR.VERSION)\n' % version)

new_version = input('Enter new version: ')

try:
    int(new_version.replace('.', ''))
except:
    print('Invalid version number, try again.')
    exit(1337)

confirm = input('Please confirm the version change from %s to %s (y/N): ' % (version, new_version))

print('\n------\n')

if confirm.lower().startswith('y'):
    print('- Updating version in onionr.py')
    
    with open('../onionr/onionr.py', 'rw') as f:
        f.write(f.read().replace("ONIONR_VERSION = '%s'" % version, "ONIONR_VERSION = '%s'" % new_version))
        
    print('- Updating version in PKGBUILD')
    
    with open('../onionr/PKGBUILD', 'rw') as f:
        f.write(f.read().replace("pkgver=%s" % version, "pkgver=%s" % new_version))
    
    print('- Committing changes')
    
    os.system('cd ..; git add onionr/onionr.py; git commit -m "Increment Onionr version to %s"' % new_version)
    
    print('- Adding tag')
    
    os.system('cd ..; git tag %s' % new_version)
    
    print('- Pushing changes')
    
    os.system('cd ..; git push origin --tags')
    
    print('\n------\n\nAll done. Create a merge request into master at this link:\n\nhttps://gitlab.com/beardog/Onionr/merge_requests/new?merge_request%5Bsource_project_id%5D=5020889&merge_request%5Btarget_branch%5D=master&merge_request%5Btarget_project_id%5D=5020889')
else:
    print('Change cancelled. No action has been taken.')


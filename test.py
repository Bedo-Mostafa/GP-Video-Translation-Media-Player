import sys
import os
import site

external_site_packages = site.getsitepackages()[1]

# If you want a single path (usually the first one is relevant)
# external_site_packages = external_site_packages[1] if external_site_packages else ""
sys.path.insert(1, external_site_packages)
print(f"Attempting to add external site-packages: {external_site_packages}")
# sys.path.insert(0, external_site_packages)
if external_site_packages and external_site_packages not in sys.path:
    print(f"Attempting to add external site-packages: {external_site_packages}")

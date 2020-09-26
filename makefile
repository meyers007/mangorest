#Packaging 
#=========
#[ ]
clean:
	\rm -rf dist build mangorest/__pycache__ setup.py.BAK mangorest.egg-info/

deploy:
	python upver.py
	VER=`cat mangorest/version.txt `
	echo "Installing VERSION: $VER" 
	
	python setup.py sdist
	python setup.py bdist_wheel --universal

	# Manually Set up for Uploading
	# ==============================
	# Create ~/.pypirc with Following Contents
	# [pypi]
	# username = andrew_schwartz
	# password = cookiesForever
	
	#Uploading
	#=========
	twine upload dist/*


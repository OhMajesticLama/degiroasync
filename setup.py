
import sys

def forbid_publish():                                              
    argv = sys.argv                                                
    blacklist = ['register', 'upload']                             
                                                                   
    for command in blacklist:                                      
        if command in argv:                                        
            print(f'Command "{command}" has been blacklisted, exiting...')
            sys.exit(2)                                            

if __name__ == '__main__':
    forbid_publish()  # Not ready for publish
    import setuptools
    setuptools.setup()
    with open("README.md", "r") as fh:
        long_description = fh.read()
							     
    setuptools.setup(                                        
	name="degiroasync",                                      
	version="0.2",                                       
	author_email="ohmajesticlama@gmail.com",             
	description="Python package for Degiro Async API", 
	long_description=long_description,                   
	#url="https://github.com/pypa/sampleproject",        
	scripts=['bin/invaist-report'],                      
	packages=setuptools.find_packages(),                 
	install_requires=[                                   
	    'yfinance>=0.1.64',                              
	    'degiro-connector>=2.0.13',                      
	    'pandas>=0.24',                                  
	    ],                                               
	classifiers=[                                        
	    "Programming Language :: Python :: 3",           
	    "License :: OSI Approved :: BSD License",        
	    "Operating System :: OS Independent",            
	],                                                   
	test_suite='nose2.collector',                         
	tests_require=['nose2']                               
    )                                                        
